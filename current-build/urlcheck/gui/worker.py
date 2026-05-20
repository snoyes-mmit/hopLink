"""Background worker for the URL-checker GUI.

Runs the full pipeline in a QThread:
    1. Open the Excel workbook (Phase 2: openpyxl)
    2. Extract URLs and record cell occurrences (Phase 2)
    3. Run the async engine over the unique URLs (Phase 1: aiohttp)
    4. Map results back to cell occurrences (Phase 2)
    5. Emit `finished` with the EnrichedResult list

The GUI thread NEVER touches engine state or Excel I/O directly. All
communication flows through `WorkerSignals` (queued cross-thread signal
connections).

Cancellation:
    - GUI thread calls `worker.request_cancel()` which sets a thread-safe
      Event.
    - Inside the asyncio loop running on the worker thread, a watchdog
      coroutine polls the Event and cancels the main pipeline task.
    - The progress callback also checks the flag and raises if set, so
      cancellation happens at the next URL boundary even if the watchdog
      is preempted.

ETA calculation:
    elapsed_per_url = elapsed_seconds / max(1, checked)
    eta_seconds     = elapsed_per_url * (total - checked)
    Smoothed lightly with a single-pole filter so the GUI doesn't jitter.
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Slot

from ..models import Classification, Settings, UrlCheckResult
from ..url_normalize import NormalizationOptions
from .signals import WorkerSignals


# ---------------------------------------------------------------------------
# Diagnostic logging
# ---------------------------------------------------------------------------

def _log_worker_exception(e: BaseException) -> None:
    """Record a worker-thread exception (with full traceback) to the app log.

    Separated from the QThread class so it has no implicit Qt dependency
    and can be unit-tested without a QApplication. Wrapped in a broad
    try/except: if logging itself fails (read-only disk, permissions),
    we silently move on — the user-facing error signal is emitted by
    `run()` regardless, so the user is never left in the dark.

    The Python stdlib `logging` module is thread-safe (each handler holds
    an I/O lock), so calling this from the worker thread is fine even
    while the GUI thread is logging its own events.
    """
    try:
        # Import locally so this module doesn't pay applog's import cost
        # on every worker run, and to keep the import graph explicit.
        from .applog import get_logger
        get_logger().exception(
            "Worker pipeline failed: %s: %s", type(e).__name__, e,
        )
    except Exception:  # noqa: BLE001 — logging must never crash the worker
        pass


# ---------------------------------------------------------------------------
# Job specification
# ---------------------------------------------------------------------------

# Sentinel value for CheckJob.column_ref meaning "scan every column in the
# sheet rather than targeting one". Kept as a module constant so the GUI
# and the worker agree on the string without typos. Anything that isn't
# this exact value goes through the normal `resolve_column` path, so
# legacy callers passing column letters / indices / header names continue
# to work unchanged.
AUTO_DETECT_ALL_COLUMNS: str = "__auto_all__"


@dataclass(frozen=True)
class CheckJob:
    """Everything the worker needs to do its job — a plain value object.

    Built by the GUI thread and handed to the worker. Plain dataclass so
    it's trivially serializable / inspectable from tests.

    `column_ref` is passed straight through to Phase 2 (`resolve_column`)
    except when it equals `AUTO_DETECT_ALL_COLUMNS`, in which case the
    worker takes the whole-sheet path (`extract_urls_from_sheet`) and
    URLs are found in any column on the chosen sheet without the user
    needing to nominate a column.
    """
    excel_path: Path
    sheet: str
    column_ref: str  # letter, index, header name, or AUTO_DETECT_ALL_COLUMNS
    header_row: Optional[int]  # 1-based; None means "no header"
    settings: Settings
    auto_https: bool = False


# ---------------------------------------------------------------------------
# Progress reporter
# ---------------------------------------------------------------------------

class _ProgressReporter:
    """Aggregates progress, computes ETA, and emits throttled updates.

    The engine's progress_cb fires once per URL — for 100k URLs that's
    too many signal emissions. We throttle to ~10 Hz so the GUI thread
    has breathing room.
    """

    def __init__(
        self,
        total: int,
        signals: WorkerSignals,
        cancel_event: threading.Event,
        emit_interval_s: float = 0.1,
    ) -> None:
        self._total = total
        self._signals = signals
        self._cancel_event = cancel_event
        self._emit_interval_s = emit_interval_s

        self._checked = 0
        self._ok = 0
        self._broken = 0
        self._blocked = 0
        self._start_time = time.monotonic()
        self._last_emit = 0.0
        self._eta_smoothed: Optional[float] = None  # exponential smoothing
        self._smoothing_alpha = 0.3

    # Suppress ETA display during the warm-up window. Reasoning:
    # - With only 1-4 URLs completed, per-URL elapsed is dominated by
    #   sampling noise: one slow URL massively inflates the first ETA
    #   the user ever sees, and they tend to judge the tool's
    #   credibility on it.
    # - We also want at least a second of wall-clock time so per-URL
    #   doesn't come out artificially small for a fast cache-hit start.
    # - Emitting 0.0 during warm-up makes the GUI render "ETA: —"
    #   (see widgets.format_eta), which is honest about the uncertainty.
    # - For runs smaller than _ETA_MIN_SAMPLES URLs total, the ETA never
    #   appears at all. That's fine because such a run finishes in
    #   seconds — there's nothing meaningful to estimate.
    _ETA_MIN_SAMPLES = 5
    _ETA_MIN_ELAPSED_S = 1.0

    def _compute_eta(self) -> float:
        if self._checked < self._ETA_MIN_SAMPLES:
            # Reset the smoothing buffer so the FIRST real ETA we emit
            # isn't blended with the (suppressed) 0.0 values from the
            # warm-up window — that would drag the first shown estimate
            # downward and make it feel like the bar is "filling up" to
            # the real value over several updates.
            self._eta_smoothed = None
            return 0.0
        elapsed = time.monotonic() - self._start_time
        if elapsed < self._ETA_MIN_ELAPSED_S:
            self._eta_smoothed = None
            return 0.0
        per_url = elapsed / self._checked
        remaining = max(0, self._total - self._checked)
        raw = per_url * remaining
        if self._eta_smoothed is None:
            self._eta_smoothed = raw
        else:
            self._eta_smoothed = (
                self._smoothing_alpha * raw
                + (1.0 - self._smoothing_alpha) * self._eta_smoothed
            )
        return max(0.0, self._eta_smoothed)

    def __call__(self, completed: int, total: int, latest: UrlCheckResult) -> None:
        # Cancellation tripwire: raise so the engine's TaskGroup unwinds.
        # This runs INSIDE the worker thread's event loop, so raising here
        # cancels in-flight work cleanly.
        if self._cancel_event.is_set():
            raise asyncio.CancelledError("Cancel requested by user")

        self._checked = completed
        if latest.classification == Classification.OK:
            self._ok += 1
        elif latest.classification == Classification.BROKEN:
            self._broken += 1
        else:
            self._blocked += 1

        now = time.monotonic()
        # Always emit on the final URL; otherwise throttle.
        if completed != total and (now - self._last_emit) < self._emit_interval_s:
            return
        self._last_emit = now
        eta = self._compute_eta()
        # Cross-thread signal emit is safe — Qt queues it on the GUI thread.
        self._signals.progress_update.emit({
            "checked": self._checked,
            "total": self._total,
            "ok": self._ok,
            "broken": self._broken,
            "blocked": self._blocked,
            "eta_seconds": eta,
        })


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

class Worker(QThread):
    """Pipeline runner. Lives entirely in its own thread.

    Lifecycle:
        w = Worker(job)
        w.signals.progress_update.connect(...)
        w.signals.finished.connect(...)
        w.signals.error.connect(...)
        w.signals.canceled.connect(...)
        w.start()    # spawns the thread; do NOT call run() directly
        w.request_cancel()  # from any thread
        w.wait()     # block-join (use with care from the GUI; usually
                     # we just listen for finished/canceled signals)
    """

    def __init__(self, job: CheckJob, parent=None) -> None:
        super().__init__(parent)
        self._job = job
        self.signals = WorkerSignals()
        # threading.Event is the right primitive: thread-safe, works with
        # Python's GIL and from outside the asyncio loop.
        self._cancel_event = threading.Event()
        # Reference to the running asyncio task, used to cancel from a
        # watchdog coroutine inside the same event loop.
        self._main_task_ref: Optional[asyncio.Task] = None

    # ----- Public cancel API (callable from GUI thread) -----

    @Slot()
    def request_cancel(self) -> None:
        """Mark this run as canceled. Safe to call from any thread.

        Setting the Event causes:
        - The progress callback to raise CancelledError on its next call.
        - The watchdog coroutine to cancel the main pipeline task.
        Either path leads to a clean unwind and a `canceled` signal.
        """
        self._cancel_event.set()

    # ----- QThread entry point -----

    def run(self) -> None:
        """Thread entry. Sets up an asyncio loop and runs the pipeline."""
        try:
            asyncio.run(self._run_pipeline())
        except asyncio.CancelledError:
            # Top-level cancellation: pipeline was stopped before completing.
            self.signals.canceled.emit()
        except Exception as e:  # noqa: BLE001 - top-level safety net
            # Log the full traceback to the rotating log file. We deliberately
            # avoid sys.stderr here: in a frozen --windowed build there is no
            # console, so prints go nowhere and the diagnostic is lost.
            # Logging via `applog` keeps the traceback in
            # %APPDATA%/urlcheck/logs (Win) / ~/Library/Logs (mac) / XDG (Linux),
            # which is exactly what support requests need.
            _log_worker_exception(e)
            self.signals.error.emit(self._format_error(e))

    # ----- Async pipeline -----

    async def _run_pipeline(self) -> None:
        """The full pipeline. Excel I/O is sync (openpyxl) so it runs in
        a thread executor to avoid blocking the asyncio event loop.
        """
        # ---- Stage 1: Excel extraction (in executor) ----
        loop = asyncio.get_running_loop()
        try:
            extraction = await loop.run_in_executor(None, self._extract_sync)
        except Exception as e:  # File errors etc. surface here.
            raise RuntimeError(self._friendly_excel_error(e)) from e

        # Emit extraction summary for the UI to show "found N URLs".
        self.signals.extraction_done.emit({
            "unique_urls": extraction.summary.unique_urls,
            "total_occurrences": extraction.summary.total_occurrences,
            "sheet": extraction.selection.sheet,
            "column_letter": extraction.selection.column_letter,
        })

        # Honor cancellation requested during extraction (rare but possible
        # for huge workbooks).
        if self._cancel_event.is_set():
            raise asyncio.CancelledError()

        # ---- Stage 2: HTTP checking ----
        unique_urls = list(extraction.unique_urls)
        if not unique_urls:
            # Nothing to check — emit an empty result list.
            self.signals.finished.emit([])
            return

        # Emit a 0/total starting frame so the UI's progress bar leaves the
        # "indeterminate" look as soon as we know the total.
        self.signals.progress_update.emit({
            "checked": 0,
            "total": len(unique_urls),
            "ok": 0, "broken": 0, "blocked": 0,
            "eta_seconds": 0.0,
        })

        reporter = _ProgressReporter(
            total=len(unique_urls),
            signals=self.signals,
            cancel_event=self._cancel_event,
        )

        # Engine import is here (not at module top) to keep import-time
        # light and to defer the aiohttp import until we actually need it.
        from ..engine import check_urls as _check_urls

        # Wrap the engine call in a task we can cancel from a watchdog.
        main_task = asyncio.create_task(
            _check_urls(unique_urls, settings=self._job.settings, progress_cb=reporter)
        )
        self._main_task_ref = main_task

        watchdog_task = asyncio.create_task(self._cancel_watchdog(main_task))

        try:
            results = await main_task
        except asyncio.CancelledError:
            raise
        finally:
            watchdog_task.cancel()
            try:
                await watchdog_task
            except (asyncio.CancelledError, Exception):
                pass

        # ---- Stage 3: enrich results with cell occurrences ----
        from ..excel_input import enrich_results_with_occurrences
        enriched = enrich_results_with_occurrences(
            results, extraction.occurrences_map
        )

        self.signals.finished.emit(enriched)

    async def _cancel_watchdog(self, task: asyncio.Task) -> None:
        """Polls the cancel Event and cancels the main task if set.

        Runs concurrently with the main pipeline. We use polling rather than
        a more elegant event-driven approach because threading.Event isn't
        directly awaitable; polling at 100 ms is well within "feels instant"
        for users and cheap on CPU.
        """
        try:
            while not task.done():
                if self._cancel_event.is_set():
                    task.cancel()
                    return
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            return

    # ----- Synchronous helpers (run in executor) -----

    def _extract_sync(self):
        """Open workbook and run Phase 2 extraction. Sync because openpyxl
        is sync; called via run_in_executor.

        Two extraction modes:

        - **Auto-detect (whole-sheet)**: when `column_ref ==
          AUTO_DETECT_ALL_COLUMNS`, we don't try to resolve a single
          column at all — we hand the workbook to
          `extract_urls_from_sheet`, which walks every cell on the
          chosen sheet and pulls URLs from anywhere. The user therefore
          doesn't need to know (or guess) which column the links are
          in.

        - **Targeted column**: otherwise, `column_ref` is a letter,
          1-based index, or header name. We resolve it via
          `resolve_column` and extract from that single column (the
          original behavior, preserved for the CLI and for users who
          explicitly nominate a column in the GUI).
        """
        from ..excel_input import (
            open_workbook,
            resolve_column,
            extract_urls,
            extract_urls_from_sheet,
        )

        wb = open_workbook(self._job.excel_path)
        opts = NormalizationOptions(
            auto_https_for_bare_domains=self._job.auto_https,
        )

        if self._job.column_ref == AUTO_DETECT_ALL_COLUMNS:
            return extract_urls_from_sheet(
                wb,
                self._job.sheet,
                header_row=self._job.header_row,
                options=opts,
            )

        selection = resolve_column(
            wb,
            self._job.sheet,
            self._job.column_ref,
            header_row=self._job.header_row,
        )
        return extract_urls(
            wb, selection, header_row=self._job.header_row, options=opts,
        )

    # ----- Error formatting -----

    @staticmethod
    def _format_error(e: BaseException) -> str:
        """Return a user-friendly one-paragraph message for the error dialog.

        Tracebacks are NOT included here — they terrify non-technical users.
        The full traceback is logged separately by `run()` via the `applog`
        rotating-file handler so power users and support staff can still
        find it after the fact (see USER_GUIDE.md → Troubleshooting).
        """
        msg = str(e)
        return msg if msg else type(e).__name__

    @staticmethod
    def _friendly_excel_error(e: BaseException) -> str:
        """Translate Excel-stage exceptions into something a colleague can
        action without a developer.

        Dispatches on the typed exception classes from `excel_input`. We
        deliberately avoid `str(e)` substring matching here — the previous
        version did, and it broke quietly whenever `excel_input`'s error
        wording was rephrased.

        Falls back to a generic message for anything we don't recognize,
        so the function is total (never raises, always returns a string).
        """
        # Import inside the function so the worker module's import-time
        # cost stays low and the dependency is explicit.
        from ..excel_input import (
            ExcelFileNotFound,
            HeaderNotFound,
            InvalidColumnReference,
            InvalidExcelFile,
            SheetNotFound,
        )

        if isinstance(e, ExcelFileNotFound):
            return (f"Could not find the Excel file:\n{e.path}\n\n"
                    "Check the path and try again.")

        if isinstance(e, InvalidExcelFile):
            # Detail from openpyxl can be useful for a power user but isn't
            # part of the headline message.
            return ("This file does not look like a valid .xlsx workbook. "
                    "If it's an older .xls, save it as .xlsx in Excel first.")

        if isinstance(e, SheetNotFound):
            available = ", ".join(e.available) if e.available else "(none)"
            return (f"Sheet {e.sheet!r} is not in this workbook.\n"
                    f"Available sheets: {available}")

        if isinstance(e, HeaderNotFound):
            return (f"Could not find a column header named {e.header!r} "
                    f"in row {e.header_row} of sheet {e.sheet!r}. "
                    "Check the column name or pick a column by letter instead.")

        if isinstance(e, InvalidColumnReference):
            return (f"That column reference ({e.column_ref!r}) doesn't "
                    f"look right: {e.reason}")

        # Generic fallback: prefer the exception's message if it has one,
        # otherwise the class name.
        msg = str(e)
        return f"Could not read the Excel file: {msg}" if msg \
            else f"Could not read the Excel file ({type(e).__name__})."
