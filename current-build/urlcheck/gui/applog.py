"""Internal logging setup.

A small, fire-and-forget logger that writes to a per-user log file. Errors,
run summaries, and unexpected exceptions go here. Normal users never see
the log; it exists for support cases ("can you send me the log?").

Log location:
    - Windows : %APPDATA%/urlcheck/logs/urlchecker.log
    - macOS   : ~/Library/Logs/urlcheck/urlchecker.log
    - Linux   : ~/.local/share/urlcheck/logs/urlchecker.log

The directory is auto-created on first write. Log rotation: 1 MB per file,
keep 3 backups. That's enough to capture context for the most recent few
runs without filling someone's disk.

We avoid `logging.basicConfig` because it has surprising global side effects
when our module is imported alongside other libraries that also call it.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGGER_NAME = "urlcheck"


def _user_log_dir() -> Path:
    """Return the platform-appropriate log directory (auto-created)."""
    sysname = platform.system()
    if sysname == "Windows":
        base = Path(os.environ.get("APPDATA", str(Path.home()))) / "urlcheck" / "logs"
    elif sysname == "Darwin":
        base = Path.home() / "Library" / "Logs" / "urlcheck"
    else:
        # XDG-style on Linux. We use data dir + /logs rather than state dir
        # because /state isn't widely supported by older distros.
        xdg = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
        base = Path(xdg) / "urlcheck" / "logs"
    base.mkdir(parents=True, exist_ok=True)
    return base


_logger: logging.Logger | None = None


def get_logger() -> logging.Logger:
    """Return the configured logger. Idempotent.

    Configures a rotating file handler the first time it's called. If
    handler setup fails (read-only filesystem, permissions, etc.), we
    silently fall back to a logger with no handlers — logging is a
    nice-to-have, not a load-bearing dependency.
    """
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    # Don't propagate to root — keeps our records out of any other
    # libraries' loggers that might be configured globally.
    logger.propagate = False

    if logger.handlers:
        # Already configured (e.g. by tests).
        _logger = logger
        return logger

    try:
        log_path = _user_log_dir() / "urlchecker.log"
        handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(handler)
    except Exception as e:  # noqa: BLE001
        # Logging itself failed. Print once to stderr (helpful in debug
        # builds where the console is visible), then move on with a
        # null-handler logger.
        sys.stderr.write(f"urlcheck: could not initialize log file: {e}\n")
        logger.addHandler(logging.NullHandler())

    _logger = logger
    return logger


def log_unhandled(exc_type, exc_value, exc_tb) -> None:
    """sys.excepthook target for catching unhandled top-level exceptions.

    Logs the traceback to the rotating file. The GUI's own try/except
    blocks should catch most things; this is a last-resort net.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # Let Ctrl-C behave normally.
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    try:
        get_logger().error(
            "Unhandled exception", exc_info=(exc_type, exc_value, exc_tb)
        )
    except Exception:
        pass
