"""Entry point for the URL Health Checker desktop GUI.

Run with:
    python app.py
or once installed:
    python -m urlcheck.gui      (see urlcheck/gui/__main__.py — optional)

This is intentionally a thin shim — all real logic lives in
urlcheck/gui/main_window.py and urlcheck/gui/worker.py.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    # Friendly error if PySide6 isn't installed — instead of an opaque
    # ModuleNotFoundError, tell the user what to do.
    try:
        from PySide6.QtWidgets import QApplication
    except ModuleNotFoundError:
        sys.stderr.write(
            "PySide6 is not installed. Install it with:\n"
            "    pip install PySide6\n"
            "Then run this script again.\n"
        )
        return 2

    # Same check for aiohttp, since the run-time path depends on it.
    try:
        import aiohttp  # noqa: F401
    except ModuleNotFoundError:
        sys.stderr.write(
            "aiohttp is not installed. Install it with:\n"
            "    pip install aiohttp\n"
            "Then run this script again.\n"
        )
        return 2

    from urlcheck.gui.applog import get_logger, log_unhandled
    from urlcheck.gui.icon import load_app_icon
    from urlcheck.gui.main_window import MainWindow, APP_TITLE

    # Last-resort exception logging.
    sys.excepthook = log_unhandled
    logger = get_logger()
    logger.info("Launching %s", APP_TITLE)

    # Smoke-test mode: import everything (the imports above already happened),
    # construct the app + window briefly, then exit 0. Used by
    # build_tools/smoke_test.py to verify a frozen build doesn't crash on
    # import. If we got this far, every required dep imported successfully.
    if os.environ.get("URLCHECK_SMOKE_TEST") == "1":
        app = QApplication(sys.argv)
        app.setApplicationName(APP_TITLE)
        app.setWindowIcon(load_app_icon())
        _ = MainWindow()
        sys.stderr.write("urlcheck smoke test: all imports OK\n")
        return 0

    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setOrganizationName("urlcheck")
    # Setting on QApplication is what gives us the right taskbar/dock icon
    # on Windows and Linux. macOS picks up the .app bundle's icon, but
    # setting it here too is harmless and helps when running via
    # `python app.py` during development.
    app.setWindowIcon(load_app_icon())
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
