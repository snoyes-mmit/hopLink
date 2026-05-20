"""Bot-protection / challenge-page signature detection.

Detection happens in two places:
1. Response headers (case-insensitive name & value matching).
2. Response body (case-insensitive substring match against the first
   `body_read_limit` bytes).

Each signature carries a human-readable "likely reason" string so the engine
can attach it to the result.

The patterns here are intentionally conservative — they target well-known
bot-protection vendors and challenge pages rather than trying to fingerprint
every possible WAF. False positives on the OK path are worse than missing
exotic blockers; missed blockers just show up as ambiguous results.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Reason strings (kept centralized so callers use consistent labels)
# ---------------------------------------------------------------------------

REASON_CLOUDFLARE = "Cloudflare bot protection"
REASON_AKAMAI = "Akamai / bot manager"
REASON_PERIMETERX = "PerimeterX challenge"
REASON_DATADOME = "DataDome protection"
REASON_429 = "Rate limited / 429"
REASON_503 = "Service unavailable / 503 — possibly throttled or blocking"
REASON_403 = "403 Forbidden — may require auth or be blocking automated checks"
REASON_REPEATED_TIMEOUT = "Repeated timeouts on a domain that otherwise succeeds"
REASON_GENERIC_CHALLENGE = "Challenge / CAPTCHA page detected in body"


# ---------------------------------------------------------------------------
# Header signatures: (header_name_lower, value_regex_or_None, reason)
# If value_regex is None, presence of the header alone triggers the match.
# ---------------------------------------------------------------------------

_HEADER_SIGNATURES: list[tuple[str, Optional[re.Pattern[str]], str]] = [
    ("server", re.compile(r"cloudflare", re.I), REASON_CLOUDFLARE),
    ("cf-mitigated", None, REASON_CLOUDFLARE),
    ("cf-chl-bypass", None, REASON_CLOUDFLARE),
    ("server", re.compile(r"akamai", re.I), REASON_AKAMAI),
    ("x-akamai-transformed", None, REASON_AKAMAI),
    ("server", re.compile(r"ghost", re.I), REASON_AKAMAI),  # Akamai "AkamaiGHost"
    ("x-px-block", None, REASON_PERIMETERX),
    ("set-cookie", re.compile(r"_px(?:hd|vid|3)?=", re.I), REASON_PERIMETERX),
    ("server", re.compile(r"datadome", re.I), REASON_DATADOME),
    ("x-dd-b", None, REASON_DATADOME),
    ("set-cookie", re.compile(r"datadome=", re.I), REASON_DATADOME),
]


# ---------------------------------------------------------------------------
# Body signatures: case-insensitive substrings -> reason
# Matched against the first body_read_limit bytes decoded as latin-1
# (latin-1 is total — never raises decode errors — and substring matching
# only needs ASCII compatibility for these markers).
# ---------------------------------------------------------------------------

_BODY_SIGNATURES: list[tuple[re.Pattern[bytes], str]] = [
    # Cloudflare
    (re.compile(rb"attention required.{0,40}cloudflare", re.I | re.S), REASON_CLOUDFLARE),
    (re.compile(rb"cf-browser-verification", re.I), REASON_CLOUDFLARE),
    (re.compile(rb"cf_chl_opt", re.I), REASON_CLOUDFLARE),
    (re.compile(rb"checking your browser before accessing", re.I), REASON_CLOUDFLARE),
    (re.compile(rb"__cf_chl_", re.I), REASON_CLOUDFLARE),
    (re.compile(rb"please enable (?:cookies|javascript)", re.I), REASON_CLOUDFLARE),
    # Akamai
    # Real Akamai denial pages always include a multi-segment reference of
    # the form "Reference #18.deadbeef.1716040123.abc". The pattern below
    # requires at least one hex-segment-with-trailing-dot after the initial
    # "#<digits>." so it doesn't fire on bibliography entries or prose like
    # "See reference #4. ..." that the looser pattern used to match.
    (re.compile(rb"reference\s*#\d+\.[0-9a-f]+\.", re.I), REASON_AKAMAI),
    (re.compile(rb"access denied.{0,80}reference", re.I | re.S), REASON_AKAMAI),
    # PerimeterX
    (re.compile(rb"px-captcha", re.I), REASON_PERIMETERX),
    (re.compile(rb"perimeterx", re.I), REASON_PERIMETERX),
    # DataDome
    (re.compile(rb"datadome", re.I), REASON_DATADOME),
    (re.compile(rb"dd_cookie_test", re.I), REASON_DATADOME),
    # Generic challenge / CAPTCHA fallback
    (re.compile(rb"verify you are a human", re.I), REASON_GENERIC_CHALLENGE),
    (re.compile(rb"are you a robot", re.I), REASON_GENERIC_CHALLENGE),
    (re.compile(rb"g-recaptcha", re.I), REASON_GENERIC_CHALLENGE),
    (re.compile(rb"hcaptcha\.com", re.I), REASON_GENERIC_CHALLENGE),
]


def detect_block_in_headers(headers) -> Optional[str]:
    """Return a likely-reason string if any header signature matches, else None.

    Accepts anything that behaves like a mapping with case-insensitive get,
    or a multidict-like object (aiohttp's CIMultiDict). Falls back to iterating
    items() so duplicate Set-Cookie headers are all examined.
    """
    if headers is None:
        return None

    # Build (name_lower, value) pairs once.
    try:
        pairs = [(str(k).lower(), str(v)) for k, v in headers.items()]
    except AttributeError:
        return None

    for sig_name, sig_value_re, reason in _HEADER_SIGNATURES:
        for name_lower, value in pairs:
            if name_lower != sig_name:
                continue
            if sig_value_re is None:
                return reason
            if sig_value_re.search(value):
                return reason
    return None


def detect_block_in_body(body: bytes) -> Optional[str]:
    """Return a likely-reason string if any body signature matches, else None.

    `body` is raw bytes (as returned by aiohttp). We do regex matching on bytes
    to avoid any decoding ambiguity.
    """
    if not body:
        return None
    for pattern, reason in _BODY_SIGNATURES:
        if pattern.search(body):
            return reason
    return None


def detect_block(headers, body: bytes) -> Tuple[Optional[str], str]:
    """Combined header + body detection.

    Returns (reason, source) where source is "headers", "body", or "" if
    no detection. Headers are checked first; body only if headers are clean.
    """
    reason = detect_block_in_headers(headers)
    if reason:
        return reason, "headers"
    reason = detect_block_in_body(body)
    if reason:
        return reason, "body"
    return None, ""


# ---------------------------------------------------------------------------
# Status-code based reasons (for 403/429/503 path)
# ---------------------------------------------------------------------------

def reason_for_status(status: int) -> Optional[str]:
    """Return a likely-reason string for status codes that imply blocking."""
    if status == 403:
        return REASON_403
    if status == 429:
        return REASON_429
    if status == 503:
        return REASON_503
    return None
