"""Core async URL-checking engine.

Public surface:
- check_urls(urls, settings, progress_cb) -> list[UrlCheckResult]

Behavior summary:
- Global concurrency capped by an asyncio.Semaphore.
- Per-domain throttling enforced by a per-domain asyncio.Lock + last-request
  timestamp; a worker holding the lock sleeps until at least
  `per_domain_delay` has elapsed since the last request to that domain.
- Per URL: HEAD first, fallback to GET on 405/501, connection error,
  or empty/invalid HEAD response. GET reads up to body_read_limit bytes
  for challenge-page detection.
- Redirects followed by aiohttp; final URL recorded.
- Retry with exponential backoff + jitter on transient errors.
- Three-way classification (OK / BROKEN / POSSIBLY_BLOCKED).
- Post-pass reclassifies "all-retries-timed-out" results to POSSIBLY_BLOCKED
  if other URLs on the same domain succeeded during the run.

The engine is deliberately UI-agnostic — Phase 2/3 (Excel + GUI) will call
check_urls directly and consume UrlCheckResult objects.
"""

from __future__ import annotations

import asyncio
import random
import time
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional
from urllib.parse import urlparse

import aiohttp

from .models import Classification, Settings, UrlCheckResult
from .signatures import detect_block, reason_for_status


# Type alias for the optional progress callback.
# Called with (completed_count, total_count, latest_result).
ProgressCb = Callable[[int, int, UrlCheckResult], None]


# Internal sentinel used to mark "this attempt timed out" so the post-pass
# can reclassify timeouts that happen on a domain where other URLs succeeded.
_TIMEOUT_MARKER = "__TIMEOUT__"


def _extract_domain(url: str) -> str:
    """Return the lowercased hostname portion of a URL (or '' if unparseable)."""
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _now_iso_utc() -> str:
    """Return the current UTC time as a Z-suffixed ISO string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class _DomainThrottle:
    """Per-domain delay enforcer.

    Each domain gets its own asyncio.Lock + a last-request timestamp.
    A worker that wants to make a request to domain D acquires D's lock,
    sleeps until at least `delay` has elapsed since the previous request,
    updates the timestamp, and releases the lock.

    This serializes per-domain pacing without serializing across domains.
    """

    def __init__(self, delay: float) -> None:
        self._delay = max(0.0, delay)
        self._locks: dict[str, asyncio.Lock] = {}
        self._last: dict[str, float] = {}
        # Guard for lazily-creating per-domain locks.
        self._lock_creation = asyncio.Lock()

    async def _get_lock(self, domain: str) -> asyncio.Lock:
        lock = self._locks.get(domain)
        if lock is not None:
            return lock
        async with self._lock_creation:
            lock = self._locks.get(domain)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[domain] = lock
            return lock

    async def wait(self, domain: str) -> None:
        if not domain or self._delay <= 0:
            return
        lock = await self._get_lock(domain)
        async with lock:
            last = self._last.get(domain, 0.0)
            now = time.monotonic()
            wait_for = (last + self._delay) - now
            if wait_for > 0:
                await asyncio.sleep(wait_for)
            self._last[domain] = time.monotonic()


def _backoff_seconds(attempt: int, settings: Settings) -> float:
    """Exponential backoff with +/- jitter.

    attempt is 1-indexed (the attempt that just FAILED).
    """
    base = settings.backoff_base * (2 ** (attempt - 1))
    jitter_span = base * settings.backoff_jitter
    return max(0.0, base + random.uniform(-jitter_span, jitter_span))


def _is_transient_status(status: int, settings: Settings) -> bool:
    """Whether a status code is worth retrying."""
    if 500 <= status <= 599:
        if status == 503 and not settings.retry_on_throttle:
            return False
        return settings.retry_on_5xx or status == 503
    if status == 429 and settings.retry_on_throttle:
        return True
    return False


async def _do_request(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    settings: Settings,
    read_body: bool,
) -> tuple[Optional[aiohttp.ClientResponse], Optional[bytes], Optional[str]]:
    """Perform a single HTTP request.

    Returns (response, body_bytes_or_None, error_detail_or_None).

    On success: response is the closed response object (body already read if
    read_body=True), body_bytes contains up to body_read_limit bytes.
    On failure: response is None and error_detail is populated. error_detail
    is set to _TIMEOUT_MARKER specifically for timeouts so the caller can
    distinguish them.
    """
    timeout = aiohttp.ClientTimeout(total=settings.timeout)
    try:
        async with session.request(
            method,
            url,
            timeout=timeout,
            allow_redirects=True,
            max_redirects=settings.max_redirects,
        ) as resp:
            body = b""
            if read_body:
                try:
                    body = await resp.content.read(settings.body_read_limit)
                except asyncio.TimeoutError:
                    return None, None, _TIMEOUT_MARKER
                except Exception as e:
                    # Body-read failure is non-fatal for classification —
                    # we still have status + headers. Treat as empty body.
                    body = b""
            return resp, body, None
    except asyncio.TimeoutError:
        return None, None, _TIMEOUT_MARKER
    except aiohttp.TooManyRedirects as e:
        return None, None, f"Too many redirects: {e}"
    except aiohttp.InvalidURL as e:
        return None, None, f"Invalid URL: {e}"
    except aiohttp.ClientSSLError as e:
        return None, None, f"SSL error: {e}"
    except aiohttp.ClientConnectorDNSError as e:  # type: ignore[attr-defined]
        return None, None, f"DNS error: {e}"
    except aiohttp.ClientConnectorError as e:
        # Covers DNS on older aiohttp + connection refused + network unreachable.
        msg = str(e)
        if "Name or service not known" in msg or "nodename nor servname" in msg:
            return None, None, f"DNS error: {msg}"
        return None, None, f"Connection error: {msg}"
    except aiohttp.ServerDisconnectedError as e:
        return None, None, f"Server disconnected: {e}"
    except aiohttp.ClientResponseError as e:
        return None, None, f"Client response error: {e}"
    except aiohttp.ClientPayloadError as e:
        return None, None, f"Payload error: {e}"
    except aiohttp.ClientError as e:
        return None, None, f"Client error: {e}"
    except UnicodeError as e:
        # IDNA/punycode failures bubble up as UnicodeError for some bad hosts.
        return None, None, f"Hostname encoding error: {e}"


def _should_fallback_to_get(
    response: Optional[aiohttp.ClientResponse],
    error_detail: Optional[str],
) -> bool:
    """Decide whether a HEAD attempt warrants a GET fallback.

    Fallback when:
    - HEAD returned 405 or 501 (method not allowed / not implemented).
    - HEAD raised a non-timeout connection-class error (some servers behave
      oddly on HEAD; we want to retry the URL with GET before declaring it
      dead).
    - HEAD returned no response object at all and the failure wasn't a timeout
      (timeouts are handled by retry, not fallback).
    """
    if response is not None:
        return response.status in (405, 501)
    if error_detail is None:
        return False
    if error_detail == _TIMEOUT_MARKER:
        return False
    # Non-timeout connection failure on HEAD -> try GET.
    return True


async def _check_one(
    url: str,
    session: aiohttp.ClientSession,
    settings: Settings,
    semaphore: asyncio.Semaphore,
    throttle: _DomainThrottle,
) -> UrlCheckResult:
    """Check a single URL with the full HEAD->GET fallback + retry pipeline."""
    domain = _extract_domain(url)
    started_wall = time.monotonic()
    attempts = 0
    method_used = ""
    last_error: Optional[str] = None

    # ----- HEAD attempts (with retries) -----
    head_response: Optional[aiohttp.ClientResponse] = None
    head_body: Optional[bytes] = None
    head_error: Optional[str] = None
    head_status: Optional[int] = None
    head_final_url: Optional[str] = None
    head_headers = None

    async with semaphore:
        for attempt_idx in range(settings.retries + 1):
            attempts += 1
            await throttle.wait(domain)
            t0 = time.monotonic()
            resp, body, err = await _do_request(
                session, "HEAD", url, settings, read_body=False
            )
            method_used = "HEAD"
            if resp is not None:
                head_response = resp
                head_body = body or b""
                head_status = resp.status
                head_final_url = str(resp.url)
                head_headers = resp.headers
                head_error = None
                # Decide whether to retry this HEAD result.
                if _is_transient_status(resp.status, settings):
                    last_error = f"HEAD HTTP {resp.status}"
                    if attempt_idx < settings.retries:
                        await asyncio.sleep(_backoff_seconds(attempt_idx + 1, settings))
                        continue
                break
            else:
                head_error = err
                last_error = err
                # Retry on timeouts and generic connection errors.
                # Don't retry obviously hopeless cases (Invalid URL).
                if err and err.startswith("Invalid URL"):
                    break
                if attempt_idx < settings.retries:
                    await asyncio.sleep(_backoff_seconds(attempt_idx + 1, settings))
                    continue
                break

        # ----- Decide whether to GET-fallback -----
        do_get = _should_fallback_to_get(head_response, head_error)

        get_response: Optional[aiohttp.ClientResponse] = None
        get_body: Optional[bytes] = None
        get_error: Optional[str] = None
        get_status: Optional[int] = None
        get_final_url: Optional[str] = None
        get_headers = None

        if do_get:
            for attempt_idx in range(settings.retries + 1):
                attempts += 1
                await throttle.wait(domain)
                resp, body, err = await _do_request(
                    session, "GET", url, settings, read_body=True
                )
                method_used = "GET"
                if resp is not None:
                    get_response = resp
                    get_body = body or b""
                    get_status = resp.status
                    get_final_url = str(resp.url)
                    get_headers = resp.headers
                    get_error = None
                    if _is_transient_status(resp.status, settings):
                        last_error = f"GET HTTP {resp.status}"
                        if attempt_idx < settings.retries:
                            await asyncio.sleep(
                                _backoff_seconds(attempt_idx + 1, settings)
                            )
                            continue
                    break
                else:
                    get_error = err
                    last_error = err
                    if err and err.startswith("Invalid URL"):
                        break
                    if attempt_idx < settings.retries:
                        await asyncio.sleep(_backoff_seconds(attempt_idx + 1, settings))
                        continue
                    break

    elapsed_ms = int((time.monotonic() - started_wall) * 1000)

    # ----- Pick the "winning" response: GET if we did one, else HEAD -----
    if do_get:
        final_status = get_status
        final_url = get_final_url
        final_headers = get_headers
        final_body = get_body or b""
        final_error = get_error
    else:
        final_status = head_status
        final_url = head_final_url
        final_headers = head_headers
        final_body = head_body or b""
        final_error = head_error

    # ----- Build the result by classifying -----
    result = UrlCheckResult(
        original_url=url,
        domain=domain,
        classification=Classification.BROKEN,  # placeholder, set below
        final_url=final_url,
        http_status=final_status,
        error_detail=None,
        likely_reason=None,
        response_time_ms=elapsed_ms,
        method_used=method_used,
        attempts=attempts,
        checked_at_utc=_now_iso_utc(),
    )

    # Case 1: no response at all -> BROKEN (or possibly-blocked-after-pass for timeouts)
    if final_status is None:
        if final_error == _TIMEOUT_MARKER:
            result.error_detail = f"Timeout after {settings.timeout:.1f}s (all retries exhausted)"
        else:
            result.error_detail = final_error or "Unknown error"
        result.classification = Classification.BROKEN
        return result

    # Case 2: response present — check for blocking signals first.
    block_reason = None
    block_source = ""

    # Signature-based detection on headers + body.
    sig_reason, sig_source = detect_block(final_headers, final_body)
    if sig_reason:
        block_reason = sig_reason
        block_source = sig_source

    # Status-based detection (403/429/503).
    status_reason = reason_for_status(final_status)
    if status_reason and not block_reason:
        block_reason = status_reason
        block_source = "status"

    if block_reason:
        result.classification = Classification.POSSIBLY_BLOCKED
        result.likely_reason = block_reason
        result.error_detail = (
            f"HTTP {final_status} — blocked indicator in {block_source}"
            if block_source != "status"
            else f"HTTP {final_status}"
        )
        return result

    # Case 3: clean 200 -> OK
    if final_status == 200:
        result.classification = Classification.OK
        result.error_detail = None
        return result

    # Case 4: redirect status that somehow wasn't followed (rare with allow_redirects=True)
    # or any other non-200, non-blocked status -> BROKEN.
    result.classification = Classification.BROKEN
    result.error_detail = f"HTTP {final_status}"
    return result


async def check_urls(
    urls: list[str],
    settings: Optional[Settings] = None,
    progress_cb: Optional[ProgressCb] = None,
) -> list[UrlCheckResult]:
    """Check a list of URLs concurrently and return results.

    The order of returned results is not guaranteed to match the input order.
    For input/output mapping (e.g. cell locations in Phase 2), callers should
    key on `original_url`.

    Args:
        urls: List of URL strings to check.
        settings: Optional Settings; defaults are used if omitted.
        progress_cb: Optional callable invoked after each URL completes with
                     (completed_count, total_count, latest_result).
    """
    settings = settings or Settings()
    if not urls:
        return []

    semaphore = asyncio.Semaphore(max(1, settings.concurrency))
    throttle = _DomainThrottle(settings.per_domain_delay)

    # Reasonable connector limits. We cap connections per host so we don't
    # accidentally hammer a single domain even if concurrency is high.
    connector = aiohttp.TCPConnector(
        limit=settings.concurrency * 2,
        limit_per_host=max(1, min(10, settings.concurrency)),
        ttl_dns_cache=300,
    )

    headers = {
        "User-Agent": settings.user_agent,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    results: list[UrlCheckResult] = []
    completed = 0
    total = len(urls)
    results_lock = asyncio.Lock()

    async with aiohttp.ClientSession(
        connector=connector,
        headers=headers,
        trust_env=True,
    ) as session:

        async def worker(u: str) -> None:
            nonlocal completed
            try:
                r = await _check_one(u, session, settings, semaphore, throttle)
            except Exception as e:  # pragma: no cover - safety net
                r = UrlCheckResult(
                    original_url=u,
                    domain=_extract_domain(u),
                    classification=Classification.BROKEN,
                    error_detail=f"Engine error: {e!r}",
                    checked_at_utc=_now_iso_utc(),
                )
            async with results_lock:
                results.append(r)
                completed += 1
                if progress_cb is not None:
                    try:
                        progress_cb(completed, total, r)
                    except Exception:
                        # Never let a bad callback crash the engine.
                        pass

        # Python 3.11 TaskGroup for clean cancellation semantics.
        async with asyncio.TaskGroup() as tg:
            for u in urls:
                tg.create_task(worker(u))

    # ----- Post-pass: reclassify timeouts on domains that otherwise succeeded -----
    _reclassify_repeated_timeouts(results)

    return results


def _reclassify_repeated_timeouts(results: list[UrlCheckResult]) -> None:
    """If a URL timed out on every attempt but other URLs on the same domain
    returned OK or any successful response, mark it POSSIBLY_BLOCKED.

    Mutates the result objects in place.
    """
    # Find domains that had at least one "successful contact" (any HTTP status
    # back, regardless of code — that proves the host is reachable).
    domains_with_contact: set[str] = set()
    for r in results:
        if r.http_status is not None and r.domain:
            domains_with_contact.add(r.domain)

    for r in results:
        if r.classification != Classification.BROKEN:
            continue
        if r.http_status is not None:
            continue
        if not r.error_detail or "Timeout" not in r.error_detail:
            continue
        if r.domain in domains_with_contact:
            r.classification = Classification.POSSIBLY_BLOCKED
            r.likely_reason = (
                "Repeated timeouts on a domain that otherwise succeeds"
            )


# ---------------------------------------------------------------------------
# Synchronous convenience wrapper
# ---------------------------------------------------------------------------

def check_urls_sync(
    urls: list[str],
    settings: Optional[Settings] = None,
    progress_cb: Optional[ProgressCb] = None,
) -> list[UrlCheckResult]:
    """Blocking wrapper around `check_urls` for non-async callers (CLI, tests)."""
    return asyncio.run(check_urls(urls, settings=settings, progress_cb=progress_cb))
