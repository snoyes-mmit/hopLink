"""Worker signal definitions for the URL-checker GUI.

PySide6 requires Signal to be declared as class attributes on a QObject
subclass — they cannot be on a QThread directly without subtle issues
with thread affinity, and they must NOT be created inside __init__.

Defining them on a separate WorkerSignals object also lets us reuse the
same signal contract for both QThread and QRunnable approaches if we
ever swap implementations.

Signals:
    progress_update(dict): Live progress payload with keys:
        - checked (int): URLs completed so far
        - total (int): Total URLs to check
        - ok (int): Count classified OK
        - broken (int): Count classified BROKEN
        - blocked (int): Count classified POSSIBLY_BLOCKED
        - eta_seconds (float): Estimated seconds remaining (>=0)

    extraction_done(dict): Emitted once after the Excel-extraction stage
        completes (before any HTTP traffic). Lets the UI show the count
        of unique URLs that will be checked. Payload:
        - unique_urls (int)
        - total_occurrences (int)
        - sheet (str)
        - column_letter (str)

    finished(list): Emitted on successful completion. The payload is the
        list of EnrichedResult objects (Phase 2's output) ready to feed
        into the Phase 3 writer.

    error(str): Emitted on unrecoverable errors. The payload is a
        user-friendly message suitable for a dialog.

    canceled(): Emitted when the worker confirms it has stopped after
        a cancel request.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class WorkerSignals(QObject):
    """Container for the worker's outgoing signals.

    A QObject is required so signals can be declared as class attributes.
    Instances are owned by the worker but emitted to the GUI thread via
    Qt's queued-connection mechanism (the default for cross-thread
    signal connections).
    """

    progress_update = Signal(dict)
    extraction_done = Signal(dict)
    finished = Signal(list)
    error = Signal(str)
    canceled = Signal()
