"""Data models for the URL checker engine.

Defines:
- Classification: result categories (OK / BROKEN / POSSIBLY_BLOCKED)
- Settings: tunable runtime configuration
- UrlCheckResult: per-URL result record
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class Classification(str, Enum):
    """Three-way classification of a checked URL."""

    OK = "OK"
    BROKEN = "BROKEN"
    POSSIBLY_BLOCKED = "POSSIBLY_BLOCKED"


@dataclass(frozen=True)
class Settings:
    """Tunable runtime settings for the engine.

    Defaults match the project spec.
    """

    concurrency: int = 25
    per_domain_delay: float = 0.25  # seconds between requests to the same domain
    timeout: float = 10.0  # total request timeout in seconds
    retries: int = 2  # number of retries (so total attempts = retries + 1)
    max_redirects: int = 10
    body_read_limit: int = 65536  # bytes of GET body to read for challenge detection
    backoff_base: float = 0.5  # base seconds for exponential backoff
    backoff_jitter: float = 0.25  # +/- jitter fraction applied to each backoff
    user_agent: str = (
        # Browser-ish UA reduces false blocks. Not stealth — we identify as a checker
        # in a comment-only sense; servers see a normal UA string.
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    # Whether to retry on 5xx (other than 503 which is treated as possibly-blocked).
    retry_on_5xx: bool = True
    # Whether to retry on 429/503 (still likely blocked, but a retry can sometimes help).
    retry_on_throttle: bool = True


@dataclass
class UrlCheckResult:
    """Result of checking a single URL."""

    original_url: str
    domain: str
    classification: Classification
    final_url: Optional[str] = None
    http_status: Optional[int] = None
    error_detail: Optional[str] = None
    likely_reason: Optional[str] = None
    response_time_ms: Optional[int] = None
    method_used: str = ""  # "HEAD" or "GET" (or "" if never connected)
    attempts: int = 0
    checked_at_utc: str = ""

    def to_dict(self) -> dict:
        """Serializable dict representation (enum -> string)."""
        d = asdict(self)
        d["classification"] = self.classification.value
        return d
