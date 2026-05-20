"""Persistent application settings via QSettings.

QSettings handles cross-platform persistence: the registry on Windows,
~/Library/Preferences on macOS, ~/.config on Linux. We use a thin wrapper
to give each persisted value a typed accessor — that way the rest of the
GUI never has to remember the QSettings key strings or the type-coercion
quirks of QSettings.value().

QSettings stores everything as strings on some platforms, so we always
pass a `type=` argument to value() — without it, you can get back the
literal string "10" instead of the int 10.

Persisted values:
    last_file           — absolute path to the last successfully-loaded .xlsx
    last_save_dir       — directory chosen in the last Save Results dialog
    last_sheet          — sheet name used in the last completed run
    last_column         — column index (1-based) used in the last completed run
    last_header_row     — header_row value (0 means "no header")
    last_auto_https     — bool
    concurrency / timeout / retries / per_domain_delay — engine settings

Why these and not everything? We persist what *meaningfully* speeds up the
next run. Drag-zone hover state, window position, etc. are deliberately
NOT persisted — they cause more "weird, my window moved" surprises than
they save in friction.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSettings

from ..models import Settings as EngineSettings


# QSettings org/app identifiers. These determine the storage path/key on
# every platform; changing them resets every user's preferences, so don't.
ORG_NAME = "urlcheck"
APP_NAME = "URL Health Checker"


class AppSettings:
    """Typed wrapper around QSettings.

    Construct one instance and reuse it. Each call to set_*() persists
    immediately (QSettings auto-syncs).
    """

    def __init__(self) -> None:
        self._q = QSettings(ORG_NAME, APP_NAME)

    # ----- File / location -----

    def last_file(self) -> Optional[Path]:
        v = self._q.value("last_file", "", type=str)
        if not v:
            return None
        p = Path(v)
        # Don't return paths to files that no longer exist — that just
        # leads to "couldn't open last file" surprises on next launch.
        return p if p.exists() else None

    def set_last_file(self, path: Path | str) -> None:
        self._q.setValue("last_file", str(path))

    def last_save_dir(self) -> Optional[Path]:
        v = self._q.value("last_save_dir", "", type=str)
        if not v:
            return None
        p = Path(v)
        return p if p.is_dir() else None

    def set_last_save_dir(self, path: Path | str) -> None:
        self._q.setValue("last_save_dir", str(path))

    # ----- Sheet / column -----

    def last_sheet(self) -> str:
        return self._q.value("last_sheet", "", type=str)

    def set_last_sheet(self, name: str) -> None:
        self._q.setValue("last_sheet", name)

    def last_column(self) -> int:
        # 0 means "not set"; the UI treats that as "use auto-detection".
        return int(self._q.value("last_column", 0, type=int))

    def set_last_column(self, column_index: int) -> None:
        self._q.setValue("last_column", int(column_index))

    def last_header_row(self) -> int:
        return int(self._q.value("last_header_row", 1, type=int))

    def set_last_header_row(self, row: int) -> None:
        self._q.setValue("last_header_row", int(row))

    def last_auto_https(self) -> bool:
        return bool(self._q.value("last_auto_https", False, type=bool))

    def set_last_auto_https(self, value: bool) -> None:
        self._q.setValue("last_auto_https", bool(value))

    # ----- Engine settings -----

    def engine_settings(self) -> EngineSettings:
        """Return an EngineSettings populated with persisted advanced values
        (or sensible defaults — see SAFE_DEFAULT_* constants below).
        """
        return EngineSettings(
            concurrency=int(self._q.value(
                "concurrency", SAFE_DEFAULT_CONCURRENCY, type=int)),
            timeout=float(self._q.value(
                "timeout", SAFE_DEFAULT_TIMEOUT, type=float)),
            retries=int(self._q.value(
                "retries", SAFE_DEFAULT_RETRIES, type=int)),
            per_domain_delay=float(self._q.value(
                "per_domain_delay", SAFE_DEFAULT_PER_DOMAIN_DELAY, type=float)),
        )

    def set_engine_settings(
        self,
        concurrency: int,
        timeout: float,
        retries: int,
        per_domain_delay: float,
    ) -> None:
        self._q.setValue("concurrency", int(concurrency))
        self._q.setValue("timeout", float(timeout))
        self._q.setValue("retries", int(retries))
        self._q.setValue("per_domain_delay", float(per_domain_delay))


# ---------------------------------------------------------------------------
# Safe defaults
# ---------------------------------------------------------------------------
# These are tuned for "non-technical user with a normal home/office network".
# Lower than the engine's library-level defaults (which target power users
# with fast connections) — concurrency of 8 is polite, completes a 10k-URL
# run in a few minutes, and is unlikely to trip rate-limits.

SAFE_DEFAULT_CONCURRENCY = 8
SAFE_DEFAULT_TIMEOUT = 10.0
SAFE_DEFAULT_RETRIES = 2
SAFE_DEFAULT_PER_DOMAIN_DELAY = 0.25
