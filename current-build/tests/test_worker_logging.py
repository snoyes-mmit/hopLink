"""Behavioral tests for `urlcheck.gui.worker` — specifically the logging
of worker-thread exceptions and the user-facing error message formatting.

PySide6 is stubbed at import time so these tests can run in any
environment, including CI machines without Qt. The stub installs only
the symbols `worker.py` actually imports (`QThread`, `Slot`) — replacing
them with no-op stand-ins so the module imports cleanly without any of
Qt's runtime baggage.

What we verify:
  - `_log_worker_exception(e)` writes a record to the applog logger that
    includes the exception type, message, AND a full traceback.
  - `_format_error(e)` returns a clean message string with NO traceback.
  - If `applog.get_logger()` itself raises, the worker survives — the
    helper swallows the error rather than re-raising into the worker
    thread's top-level except.
  - The `print(... file=sys.stderr)` from the pre-fix implementation is
    gone — nothing in worker.run()'s error path writes to stderr.

Run with:
    python -m unittest tests.test_worker_logging -v
"""

from __future__ import annotations

import io
import logging
import sys
import types
import unittest
import unittest.mock


# ---------------------------------------------------------------------------
# PySide6 stub — installed BEFORE importing worker.
# ---------------------------------------------------------------------------

def _install_pyside6_stub() -> None:
    """Insert a minimal `PySide6.QtCore` into sys.modules so worker imports."""
    if "PySide6" in sys.modules:
        return  # Real PySide6 is available — use it.

    pyside6 = types.ModuleType("PySide6")
    qtcore = types.ModuleType("PySide6.QtCore")

    class _QThreadStub:
        """Stand-in for QThread. Inherits from object — we never call .start()
        in these tests, only construct and invoke methods directly.
        """
        def __init__(self, *args, **kwargs):
            pass

    class _QObjectStub:
        """Stand-in for QObject. Just enough surface for WorkerSignals."""
        def __init__(self, *args, **kwargs):
            pass

    class _SignalStub:
        """Stand-in for PySide6.Signal. Accepts the type-spec args used at
        class-definition time and provides a no-op .emit / .connect surface.
        """
        def __init__(self, *_args, **_kwargs):
            pass

        def emit(self, *_args, **_kwargs):
            pass

        def connect(self, *_args, **_kwargs):
            pass

    def _slot_stub(*_args, **_kwargs):
        """@Slot decorator stub — returns the decorated function unchanged."""
        def decorator(fn):
            return fn
        # Allow both `@Slot` (no parens) and `@Slot()` styles by handling
        # the case where it's used as a bare decorator.
        if len(_args) == 1 and callable(_args[0]) and not _kwargs:
            return _args[0]
        return decorator

    qtcore.QThread = _QThreadStub
    qtcore.QObject = _QObjectStub
    qtcore.Signal = _SignalStub
    qtcore.Slot = _slot_stub

    pyside6.QtCore = qtcore
    sys.modules["PySide6"] = pyside6
    sys.modules["PySide6.QtCore"] = qtcore


_install_pyside6_stub()

# Now safe to import worker.
from urlcheck.gui import worker as worker_mod  # noqa: E402


# ---------------------------------------------------------------------------
# Helper: capture logger output
# ---------------------------------------------------------------------------

class _LogCapture:
    """Attach an in-memory handler to the applog logger for the duration of a test.

    Restores the original handler list afterward so we don't pollute other
    tests (or the user's actual log file).
    """

    def __init__(self):
        from urlcheck.gui.applog import LOGGER_NAME
        self._logger = logging.getLogger(LOGGER_NAME)
        self._buffer = io.StringIO()
        self._handler = logging.StreamHandler(self._buffer)
        self._handler.setFormatter(logging.Formatter(
            "%(levelname)s %(message)s"
        ))
        self._original_handlers = list(self._logger.handlers)
        self._original_level = self._logger.level

    def __enter__(self):
        # Replace handlers entirely so writes don't reach the user's real log.
        self._logger.handlers = [self._handler]
        self._logger.setLevel(logging.DEBUG)
        return self

    def __exit__(self, *exc):
        self._logger.handlers = self._original_handlers
        self._logger.setLevel(self._original_level)

    @property
    def text(self) -> str:
        self._handler.flush()
        return self._buffer.getvalue()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class LogWorkerExceptionTests(unittest.TestCase):
    """`_log_worker_exception` should write a full traceback to applog."""

    def _trigger_via_log_helper(self, exc):
        """Raise + catch `exc` so the helper sees a real exc_info chain."""
        try:
            raise exc
        except Exception as e:
            worker_mod._log_worker_exception(e)

    def test_records_exception_type_and_message(self):
        with _LogCapture() as cap:
            self._trigger_via_log_helper(ValueError("bad column 'XYZ'"))
        self.assertIn("ValueError", cap.text)
        self.assertIn("bad column 'XYZ'", cap.text)

    def test_records_full_traceback(self):
        with _LogCapture() as cap:
            self._trigger_via_log_helper(RuntimeError("kaboom"))
        # `logger.exception` includes a "Traceback (most recent call last):"
        # block — the smoking gun that distinguishes this from a plain
        # error-message log.
        self.assertIn("Traceback (most recent call last)", cap.text)
        self.assertIn("RuntimeError: kaboom", cap.text)

    def test_logs_at_error_level(self):
        with _LogCapture() as cap:
            self._trigger_via_log_helper(ValueError("oops"))
        # Format we configured in _LogCapture starts with the levelname.
        self.assertTrue(cap.text.startswith("ERROR "),
                        f"expected ERROR-level log, got: {cap.text!r}")

    def test_silently_survives_logger_failure(self):
        """If `get_logger()` raises, the helper must NOT propagate it.

        Otherwise the worker thread's top-level except wouldn't catch the
        secondary error and the canceled/error signals wouldn't fire.
        """
        with unittest.mock.patch(
            "urlcheck.gui.applog.get_logger",
            side_effect=RuntimeError("logging is broken"),
        ):
            # Must not raise.
            try:
                worker_mod._log_worker_exception(ValueError("primary error"))
            except Exception as e:
                self.fail(f"_log_worker_exception leaked an exception: {e!r}")


class FormatErrorTests(unittest.TestCase):
    """`_format_error` should produce a clean dialog string with no traceback."""

    def test_returns_exception_message(self):
        msg = worker_mod.Worker._format_error(
            ValueError("Sheet 'foo' not in workbook")
        )
        self.assertEqual(msg, "Sheet 'foo' not in workbook")

    def test_falls_back_to_class_name_for_empty_message(self):
        class Custom(Exception):
            pass
        msg = worker_mod.Worker._format_error(Custom())
        self.assertEqual(msg, "Custom")

    def test_no_traceback_in_output(self):
        """The dialog message must NOT contain a traceback under any branch."""
        try:
            raise RuntimeError("kaboom")
        except RuntimeError as e:
            msg = worker_mod.Worker._format_error(e)
        self.assertNotIn("Traceback", msg)
        self.assertNotIn("File \"", msg)


class StderrNotWrittenTests(unittest.TestCase):
    """The pre-fix code did `print(tb, file=sys.stderr)`. Confirm it's gone."""

    def test_format_error_does_not_write_to_stderr(self):
        captured = io.StringIO()
        original = sys.stderr
        sys.stderr = captured
        try:
            worker_mod.Worker._format_error(RuntimeError("kaboom"))
        finally:
            sys.stderr = original
        self.assertEqual(captured.getvalue(), "",
                         "format_error must not write to stderr (frozen "
                         "builds have no stderr — diagnostics would be lost)")

    def test_log_helper_does_not_write_to_stderr(self):
        """The helper must route via applog, not stderr."""
        captured = io.StringIO()
        original = sys.stderr
        sys.stderr = captured
        # Suppress the applog write too so we're isolating stderr.
        with _LogCapture():
            try:
                try:
                    raise RuntimeError("x")
                except RuntimeError as e:
                    worker_mod._log_worker_exception(e)
            finally:
                sys.stderr = original
        self.assertEqual(captured.getvalue(), "")


class TracebackImportRemovedTests(unittest.TestCase):
    """Smoke check: the `traceback` module is no longer imported by worker.py.

    Not a behavioral assertion, but a useful guard: the import was only
    there to feed `traceback.format_exc()` into the (removed) stderr print.
    Leaving the import would be dead weight that signals to readers we're
    still doing the old pattern.
    """

    def test_worker_module_does_not_import_traceback(self):
        # `import traceback` would put `traceback` in the module's
        # globals. We check there because that's where `import` puts
        # names — robust to refactors that move things around.
        self.assertNotIn(
            "traceback", worker_mod.__dict__,
            "worker.py still imports traceback — the diagnostic is now "
            "routed via applog, so this import is dead weight.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
