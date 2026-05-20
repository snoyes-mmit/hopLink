"""URL normalization and parsing helpers for the Excel input layer.

Handles:
- Splitting cells that contain multiple URLs (whitespace / newline / comma /
  semicolon separated)
- Trimming surrounding whitespace and punctuation
- Normalizing schemes (www. -> https://, optional auto-https for bare domains)
- Rejecting non-http(s) URLs (mailto:, javascript:, anchors, "N/A", etc.)

Kept separate from excel_input.py so the rules can be unit-tested without
touching openpyxl, and reused by future phases (e.g. a "URL paste" mode).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse


# --- Regexes -----------------------------------------------------------------

# Catches the *start* of a URL-ish token. Used to find URLs embedded inside
# longer cell text. Conservative: must start with http/https or www.
_URL_FINDER = re.compile(
    r"""(?xi)
    (?<![A-Za-z0-9])              # not preceded by an ident char (avoid joining)
    (?:
        https?://[^\s,;]+         # explicit scheme
      | www\.[^\s,;]+             # bare www.
    )
    """
)

# Final-shape validator. Replaces an older `[^\s/$.?#][^\s]*$`-style regex
# that empirically rejected the obvious-bad cases (empty host, whitespace
# in host) but ALSO accepted nonsense hosts like `https://*invalid*.com`
# and `https://example..com`. The structured form below uses urlparse so
# host-shape rules live in one place and "what counts as a real host" is
# explicit rather than implicit in a regex character class.
#
# We deliberately remain LENIENT here:
# - The HTTP engine has its own error handling for malformed targets, so
#   letting a borderline URL through just produces one BROKEN row in the
#   report; rejecting a legitimate URL silently DROPS data from the
#   report (much worse for a non-technical user reviewing results).
# - Legitimate but unusual cases must pass: IDN punycode, IP literals,
#   userinfo (`user:pass@host`), trailing-dot FQDNs, non-default ports.

# Characters never valid anywhere in a netloc. (Whitespace is implied by
# control-char detection below; we list it separately for readability.)
_INVALID_NETLOC_CHARS: frozenset[str] = frozenset(
    " \t\n\r\f\v"      # any whitespace
    "<>\"`{}|\\^*"     # RFC 3986 says these are reserved-but-invalid in host
)


def _is_valid_http_url(token: str) -> bool:
    """Return True if `token` is a structurally valid http(s) URL.

    Required:
    - Scheme is http or https (case-insensitive).
    - netloc is non-empty and contains no control characters or other
      invalid host chars.
    - At least one alphanumeric character in netloc (i.e. it's not just
      punctuation).

    Not checked here (deliberately):
    - DNS resolvability — that's the engine's job.
    - "Real" TLDs — we accept localhost, intranet hostnames, IPs.
    - Path/query/fragment shape — RFC-strict validation would reject
      URLs that browsers happily fetch.
    """
    try:
        parsed = urlparse(token)
    except (ValueError, TypeError):
        return False

    if parsed.scheme.lower() not in ("http", "https"):
        return False

    netloc = parsed.netloc
    if not netloc:
        return False

    # Reject any control characters or other host-invalid chars. urlparse
    # is permissive — it will happily return netloc="*invalid*.com" — so
    # this is the gate that catches that case.
    for ch in netloc:
        if ord(ch) < 0x20 or ch in _INVALID_NETLOC_CHARS:
            return False

    # netloc must contain at least one alphanumeric character. This
    # rejects degenerate hosts like "..." or ":::" while accepting IDN
    # punycode, IPs, and userinfo-prefixed hosts.
    if not any(ch.isalnum() for ch in netloc):
        return False

    return True

# Pure-punctuation characters that always peel from the right edge.
# Brackets/parens are handled separately by `_strip_edges` because peeling
# them naively breaks legitimate URLs (Wikipedia "Foo_(bar)", MS Docs
# "String.Format(System.String,System.Object)").
_TRAILING_PUNCT_STRIP = ".,;:!?\"'`"
# Quote-like leading characters always peel. Opening brackets/parens are
# handled separately so we don't strip a paren that matches a closer later
# in the URL.
_LEADING_QUOTE_STRIP = "\"'`"

# Bracket pairs we balance-check when stripping edges. Order matters only
# for readability — each pair is independent.
_BRACKET_PAIRS: tuple[tuple[str, str], ...] = (
    ("(", ")"),
    ("[", "]"),
    ("{", "}"),
    ("<", ">"),
)
_OPENERS: frozenset[str] = frozenset(pair[0] for pair in _BRACKET_PAIRS)
_CLOSERS: frozenset[str] = frozenset(pair[1] for pair in _BRACKET_PAIRS)
_CLOSER_TO_OPENER: dict[str, str] = {close: open_ for open_, close in _BRACKET_PAIRS}
_OPENER_TO_CLOSER: dict[str, str] = {open_: close for open_, close in _BRACKET_PAIRS}

# Tokens that explicitly mean "no value" in spreadsheets.
_REJECT_LITERALS = {
    "", "n/a", "na", "none", "null", "-", "—", "–", "#", "tbd", "todo",
}

# Schemes we explicitly recognize but do NOT want to check.
_NON_CHECKABLE_SCHEMES = (
    "mailto:", "tel:", "javascript:", "ftp:", "file:", "sms:", "data:",
    "skype:", "ms-", "callto:",
)


@dataclass(frozen=True)
class NormalizationOptions:
    """Tunables for URL normalization behavior."""
    # If a URL starts with "www.", prefix "https://".
    promote_www_to_https: bool = True
    # If a token has no scheme but otherwise looks like a domain/path, prefix
    # "https://". Off by default — too easy to misfire on freeform text.
    auto_https_for_bare_domains: bool = False


def _looks_like_bare_domain(token: str) -> bool:
    """Heuristic: does a scheme-less token look like a domain?

    Used only when `auto_https_for_bare_domains=True`. Requires at least one
    dot, a TLD-ish suffix, and no whitespace.
    """
    if not token or " " in token:
        return False
    # Must have a dot and not start/end with one.
    if "." not in token or token.startswith(".") or token.endswith("."):
        return False
    head = token.split("/", 1)[0]
    parts = head.split(".")
    if len(parts) < 2:
        return False
    tld = parts[-1]
    # TLD: 2+ alpha chars (letters only — "co", "io", "com", "museum", etc).
    if not tld.isalpha() or len(tld) < 2:
        return False
    return True


def _strip_edges(token: str) -> str:
    """Strip surrounding whitespace and punctuation that commonly clings to URLs.

    Pure punctuation (".,;:!?\"'`") on either edge is peeled unconditionally.
    Brackets and parentheses are handled with balance awareness so that
    legitimate URLs containing parens (Wikipedia "Foo_(bar)", MS Docs
    "String.Format(System.String,System.Object)") survive intact.

    Algorithm (per iteration; loop until no edge can be peeled):
      1. If first AND last form a matching bracket pair (e.g. "(" and ")"),
         peel both. This handles wrapping like "(URL)" or "[URL]" without
         needing to know whether the inner URL has its own brackets.
      2. Otherwise, peel a leading opener only if it has no matching closer
         in the rest of the token (i.e., it's orphaned junk).
      3. Peel any trailing punctuation char (".,;:!?'\"`").
      4. Peel a trailing closer only if it has no matching opener in the
         body before it (i.e., it's orphaned junk like "https://x.com)").
      5. Peel leading/trailing quote chars unconditionally.

    Examples:
        "(https://example.com)."         -> "https://example.com"
        "https://wiki.org/Foo_(bar)"     -> "https://wiki.org/Foo_(bar)"   (kept)
        "https://wiki.org/Foo_(bar)."    -> "https://wiki.org/Foo_(bar)"   (dot peels,
                                                                          paren stays)
        "[https://example.com]"          -> "https://example.com"
        "https://msdn.com/api/M(a,b)"    -> "https://msdn.com/api/M(a,b)"  (kept)
        "(https://example.com"           -> "https://example.com"          (orphan peeled)
    """
    token = token.strip()
    if not token:
        return token

    changed = True
    while changed and token:
        changed = False

        # ----- Rule 1: matching bracket-pair wrap -----
        if len(token) >= 2 and token[0] in _OPENERS:
            expected_closer = _OPENER_TO_CLOSER[token[0]]
            if token[-1] == expected_closer:
                token = token[1:-1]
                changed = True
                continue  # restart with the trimmed token

        # ----- Rule 5a: leading quote -----
        if token and token[0] in _LEADING_QUOTE_STRIP:
            token = token[1:]
            changed = True

        # ----- Rule 2: orphan leading opener -----
        if token and token[0] in _OPENERS:
            closer = _OPENER_TO_CLOSER[token[0]]
            rest = token[1:]
            if _count(rest, closer) == 0:
                # No matching closer anywhere — pure junk.
                token = rest
                changed = True

        # ----- Rule 3: trailing punctuation -----
        if token and token[-1] in _TRAILING_PUNCT_STRIP:
            token = token[:-1]
            changed = True

        # ----- Rule 4: orphan trailing closer -----
        if token and token[-1] in _CLOSERS:
            opener = _CLOSER_TO_OPENER[token[-1]]
            body = token[:-1]
            if _count(body, opener) == 0:
                token = body
                changed = True

    return token


def _count(s: str, ch: str) -> int:
    """Count occurrences of a single character in a string.

    Tiny helper kept private so `_strip_edges` reads cleanly. The intent at
    each call site is "how many openers/closers are in this segment?"; the
    named helper makes that clearer than inline `.count()`.
    """
    return s.count(ch)


def normalize_url(
    raw: str,
    options: Optional[NormalizationOptions] = None,
) -> Optional[str]:
    """Normalize a single token into an http(s) URL or return None to reject.

    Returns None for empty strings, sentinel "no value" tokens, non-http
    schemes, and anything that doesn't look like a real URL after cleanup.
    """
    if raw is None:
        return None
    options = options or NormalizationOptions()

    token = _strip_edges(str(raw))
    if not token:
        return None

    lower = token.lower()
    if lower in _REJECT_LITERALS:
        return None

    # Internal anchor only.
    if token.startswith("#"):
        return None

    # Reject non-checkable schemes early.
    for scheme in _NON_CHECKABLE_SCHEMES:
        if lower.startswith(scheme):
            return None

    # Promote www. to https://www.
    if lower.startswith("www."):
        if not options.promote_www_to_https:
            return None
        token = "https://" + token

    # Auto-https for bare domains (off by default).
    if not re.match(r"^https?://", token, re.I):
        if options.auto_https_for_bare_domains and _looks_like_bare_domain(token):
            token = "https://" + token
        else:
            return None

    # Final shape validation.
    if not _is_valid_http_url(token):
        return None

    return token


def split_cell_into_tokens(cell_text: str) -> list[str]:
    """Split a cell's display text into URL candidate tokens.

    Strategy:
    1. First try to find clear http(s)://... or www. tokens with a regex —
       this handles "see https://a.com and https://b.com please" correctly.
    2. If no regex hits but the cell contains separators, fall back to
       splitting on whitespace, commas, semicolons, and pipes.
    3. Otherwise return the cell as a single token.

    The caller still passes each token through `normalize_url` for final
    validation, so this stage only needs to produce *candidates*.
    """
    if cell_text is None:
        return []
    text = str(cell_text).strip()
    if not text:
        return []

    # Pass 1: regex-extract obvious URLs.
    found = _URL_FINDER.findall(text)
    if found:
        return [t.strip() for t in found if t.strip()]

    # Pass 2: separator-split for cells like "a.com; b.com, c.com".
    if any(sep in text for sep in (",", ";", "|", "\n", "\r", "\t")):
        parts = re.split(r"[\s,;|]+", text)
        return [p for p in parts if p]

    # Pass 3: single token.
    return [text]


def extract_urls_from_text(
    cell_text: str,
    options: Optional[NormalizationOptions] = None,
) -> list[str]:
    """End-to-end: take a cell's text, return normalized http(s) URLs.

    Order is preserved; duplicates within the same cell are kept (the caller
    deduplicates globally).
    """
    out: list[str] = []
    for token in split_cell_into_tokens(cell_text):
        normalized = normalize_url(token, options)
        if normalized:
            out.append(normalized)
    return out
