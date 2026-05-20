"""Behavioral tests for ETA warm-up suppression in `_ProgressReporter`.

The previous implementation computed an ETA from the very first completed
URL. With only 1-4 samples, per-URL elapsed is dominated by sampling
noise — a single slow URL produced a massively inflated first ETA. That's
the value the user judges the tool's credibility on, so it matters.

The new behavior suppresses ETA (returns 0.0, which `format_eta` renders
as "—") for a small warm-up window, then emits a stable estimate once
enough samples and enough wall-clock time have accumulated.

These tests stub PySide6 and capture emitted progress payloads via a
recording signal object, so they run with no Qt installed and are fully
deterministic with respect to wall-clock time (we drive `time.monotonic`
through `unittest.mock`).

Run with:
    python -m unittest tests.test_worker_eta_warmup -v
"""

from __future__ import annotations

import sys
import threading
import types
import unittest
import unittest.mock


# ---------------------------------------------------------------------------
# PySide6 stub (same pattern as test_worker_logging.py)
# ---------------------------------------------------------------------------

def _install_pyside6_stub() -> None:
    if "PySide6" in sys.modules and hasattr(
        sys.modules.get("PySide6.QtCore"), "QThread"
    ):
        return

    pyside6 = sys.modules.get("PySide6") or types.ModuleType("PySide6")
    qtcore = sys.modules.get("PySide6.QtCore") or types.ModuleType("PySide6.QtCore")

    class _QThreadStub:
        def __init__(self, *a, **kw):
            pass

    class _QObjectStub:
        def __init__(self, *a, **kw):
            pass

    class _SignalStub:
        def __init__(self, *a, **kw):
            pass

        def emit(self, *a, **kw):
            pass

        def connect(self, *a, **kw):
            pass

    def _slot_stub(*a, **kw):
        def decorator(fn):
            return fn
        if len(a) == 1 and callable(a[0]) and not kw:
            return a[0]
        return decorator

    qtcore.QThread = _QThreadStub
    qtcore.QObject = _QObjectStub
    qtcore.Signal = _SignalStub
    qtcore.Slot = _slot_stub
    pyside6.QtCore = qtcore
    sys.modules["PySide6"] = pyside6
    sys.modules["PySide6.QtCore"] = qtcore


_install_pyside6_stub()

# Import after the stub is in place.
from urlcheck.gui import worker as worker_mod  # noqa: E402
from urlcheck.models import Classification, UrlCheckResult  # noqa: E402


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

class _RecordingSignals:
    """Stand-in for WorkerSignals.progress_update — records every emit."""

    def __init__(self):
        self.progress_update = self
        self.emitted: list[dict] = []

    def emit(self, payload: dict) -> None:
        # Copy so later mutations don't retroactively edit our records.
        self.emitted.append(dict(payload))


def _ok_result(url: str) -> UrlCheckResult:
    return UrlCheckResult(
        original_url=url,
        domain=url.split("//", 1)[-1].split("/", 1)[0],
        classification=Classification.OK,
        http_status=200,
    )


def _make_reporter(total: int, *, emit_interval_s: float = 0.0):
    """Build a reporter wired to a fresh recorder, with throttling off
    (emit_interval_s=0) so every call produces an emission. Cancel
    event is unset.
    """
    signals = _RecordingSignals()
    return worker_mod._ProgressReporter(
        total=total,
        signals=signals,
        cancel_event=threading.Event(),
        emit_interval_s=emit_interval_s,
    ), signals


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class WarmupSuppressesEarlyEta(unittest.TestCase):
    """During the warm-up window (< _ETA_MIN_SAMPLES URLs), eta_seconds
    must be 0 regardless of how long the first URL took.

    0 is the contract that makes `format_eta` render "—" in the GUI.
    """

    def test_warmup_constants_are_sane(self):
        # Sanity guards in case someone tweaks the constants later.
        self.assertGreaterEqual(worker_mod._ProgressReporter._ETA_MIN_SAMPLES, 2,
                                "Need at least 2 samples for a meaningful estimate.")
        self.assertGreater(worker_mod._ProgressReporter._ETA_MIN_ELAPSED_S, 0.0)

    def test_first_url_eta_is_zero_even_with_slow_first_url(self):
        """The headline regression case: one slow first URL must NOT
        produce an inflated headline ETA.
        """
        reporter, signals = _make_reporter(total=100)
        # Patch time.monotonic so we can simulate "60s elapsed by the
        # time URL #1 completes" without actually waiting.
        with unittest.mock.patch.object(worker_mod.time, "monotonic") as clock:
            clock.return_value = 0.0
            reporter._start_time = clock.return_value
            # 60s later, the first URL completes.
            clock.return_value = 60.0
            reporter(1, 100, _ok_result("https://a.com"))

        self.assertEqual(len(signals.emitted), 1)
        self.assertEqual(signals.emitted[-1]["eta_seconds"], 0.0,
                         "First-URL ETA must be suppressed (== 0), "
                         "even though raw per-url would be 60s * 99 remaining "
                         "= 5940s of nonsense.")

    def test_eta_suppressed_below_min_samples(self):
        """Each completion below the threshold should yield eta=0."""
        reporter, signals = _make_reporter(total=100)
        min_samples = worker_mod._ProgressReporter._ETA_MIN_SAMPLES

        with unittest.mock.patch.object(worker_mod.time, "monotonic") as clock:
            clock.return_value = 0.0
            reporter._start_time = clock.return_value
            # Step through URLs 1..(min_samples - 1) at 1s each.
            for i in range(1, min_samples):
                clock.return_value = float(i)
                reporter(i, 100, _ok_result(f"https://a{i}.com"))

        self.assertEqual(len(signals.emitted), min_samples - 1)
        for idx, payload in enumerate(signals.emitted, start=1):
            self.assertEqual(
                payload["eta_seconds"], 0.0,
                f"URL #{idx} during warm-up should have eta_seconds=0, "
                f"got {payload['eta_seconds']}",
            )

    def test_eta_suppressed_below_min_elapsed(self):
        """Even after enough samples, if elapsed < min, still suppress.

        Hypothetical: 10 URLs returned cached responses in 0.3s total.
        per_url would be 0.03s and the ETA estimate would be wildly
        optimistic. Wait for at least a real second of wall-clock.
        """
        reporter, signals = _make_reporter(total=100)
        min_elapsed = worker_mod._ProgressReporter._ETA_MIN_ELAPSED_S

        with unittest.mock.patch.object(worker_mod.time, "monotonic") as clock:
            clock.return_value = 0.0
            reporter._start_time = 0.0
            # 10 URLs complete in less than min_elapsed (use half).
            min_samples = worker_mod._ProgressReporter._ETA_MIN_SAMPLES
            n_urls = max(10, min_samples + 5)
            for i in range(1, n_urls + 1):
                clock.return_value = (min_elapsed / 2.0) * (i / n_urls)
                reporter(i, 100, _ok_result(f"https://a{i}.com"))

        for payload in signals.emitted:
            self.assertEqual(
                payload["eta_seconds"], 0.0,
                "Should suppress when elapsed wall-clock is too small, "
                "even with enough samples.",
            )


class EtaAppearsAfterWarmup(unittest.TestCase):
    """Once the warm-up window has passed, a positive ETA must appear."""

    def test_eta_is_positive_once_thresholds_met(self):
        reporter, signals = _make_reporter(total=100)
        min_samples = worker_mod._ProgressReporter._ETA_MIN_SAMPLES
        min_elapsed = worker_mod._ProgressReporter._ETA_MIN_ELAPSED_S

        with unittest.mock.patch.object(worker_mod.time, "monotonic") as clock:
            clock.return_value = 0.0
            reporter._start_time = 0.0
            # Step through enough URLs at a stable cadence to clear BOTH
            # thresholds. 10 URLs over 10 seconds → 1 URL/s, 90 left → 90s ETA.
            n = max(min_samples + 5, 10)
            elapsed_per_step = max(min_elapsed / n, 1.0)
            for i in range(1, n + 1):
                clock.return_value = elapsed_per_step * i
                reporter(i, 100, _ok_result(f"https://a{i}.com"))

        # Last emission should have a positive ETA.
        last = signals.emitted[-1]
        self.assertGreater(last["eta_seconds"], 0.0,
                           f"After warm-up the ETA should appear, "
                           f"got {last}")

    def test_eta_estimate_is_in_expected_range(self):
        """At 1 URL/s with 90 URLs remaining, ETA should be ~90s, not 5940s
        (which is what the old code would produce on a single slow URL)
        and not 0 (which is the warm-up sentinel).
        """
        reporter, signals = _make_reporter(total=100)
        with unittest.mock.patch.object(worker_mod.time, "monotonic") as clock:
            clock.return_value = 0.0
            reporter._start_time = 0.0
            # 10 URLs in 10 seconds — clear cadence, well past warm-up.
            for i in range(1, 11):
                clock.return_value = float(i)
                reporter(i, 100, _ok_result(f"https://a{i}.com"))

        # 90 URLs remaining at 1s each → ~90s. Allow a wide range because
        # smoothing may pull the first emission below the raw value; we
        # just want "sane order of magnitude", not exact arithmetic.
        last = signals.emitted[-1]
        self.assertGreater(last["eta_seconds"], 30.0)
        self.assertLess(last["eta_seconds"], 200.0)

    def test_first_real_eta_is_not_blended_with_zero(self):
        """Smoothing buffer must reset between warm-up and first real ETA.

        Otherwise the GUI shows a value much lower than the actual rate
        for the next few frames, which feels like a misleading "filling
        up" animation rather than an honest first estimate.
        """
        reporter, signals = _make_reporter(total=100)
        with unittest.mock.patch.object(worker_mod.time, "monotonic") as clock:
            clock.return_value = 0.0
            reporter._start_time = 0.0
            # Walk through warm-up — all suppressed.
            for i in range(1, worker_mod._ProgressReporter._ETA_MIN_SAMPLES):
                clock.return_value = float(i)
                reporter(i, 100, _ok_result(f"https://a{i}.com"))
            # Now the first sample BEYOND the threshold — must be
            # ~per_url * remaining, NOT a 70%-blend of 0 + raw.
            first_real_idx = worker_mod._ProgressReporter._ETA_MIN_SAMPLES
            clock.return_value = float(first_real_idx)
            reporter(first_real_idx, 100, _ok_result("https://real.com"))

        last = signals.emitted[-1]
        # At first_real_idx URLs in first_real_idx seconds → per_url=1.0,
        # remaining=(100 - first_real_idx), so raw_eta ≈ 100 - first_real_idx.
        first_real_eta = last["eta_seconds"]
        remaining = 100 - first_real_idx
        # The first real emission should be CLOSE to the raw rate, not
        # massively below it (which would happen if a buffered 0 leaked
        # through smoothing).
        self.assertGreater(
            first_real_eta, remaining * 0.6,
            f"First real ETA ({first_real_eta}) seems blended with "
            f"the suppressed-warm-up 0; expected ~{remaining}.",
        )


class WarmupIsStateful(unittest.TestCase):
    """Once we exit warm-up, going BACK below the sample threshold is
    impossible by construction (completed only increases). But other
    state interactions matter — verify they don't regress.
    """

    def test_emits_at_completion_even_during_warmup(self):
        """The reporter has logic that "always emits on the final URL".
        If total < min_samples, that final emission still happens — but
        with eta=0 since we're still in warm-up.
        """
        reporter, signals = _make_reporter(total=2)
        with unittest.mock.patch.object(worker_mod.time, "monotonic") as clock:
            clock.return_value = 0.0
            reporter._start_time = 0.0
            clock.return_value = 1.0
            reporter(1, 2, _ok_result("https://a.com"))
            clock.return_value = 2.0
            reporter(2, 2, _ok_result("https://b.com"))

        # Two emissions, both during warm-up since min_samples > 2.
        self.assertEqual(len(signals.emitted), 2)
        for payload in signals.emitted:
            self.assertEqual(payload["eta_seconds"], 0.0)
        # Counters should still be accurate even when ETA is suppressed.
        self.assertEqual(signals.emitted[-1]["checked"], 2)
        self.assertEqual(signals.emitted[-1]["ok"], 2)


class FormatEtaTreatsZeroAsUnknown(unittest.TestCase):
    """End-to-end sanity: the value the reporter emits during warm-up
    must render as "—" in the GUI. This documents the contract between
    the worker and `widgets.format_eta`.
    """

    def test_zero_renders_as_dash(self):
        # Local import to avoid pulling widgets at module level (it
        # imports PySide6 widgets; the stub above doesn't cover those).
        import ast
        from pathlib import Path
        # Pull the pure-Python format_eta function out of widgets.py
        # without importing the module (which depends on QtWidgets).
        src = (Path(worker_mod.__file__).parent / "widgets.py").read_text()
        tree = ast.parse(src)
        fn = next(n for n in tree.body
                  if isinstance(n, ast.FunctionDef) and n.name == "format_eta")
        ns: dict = {}
        exec(compile(ast.Module(body=[fn], type_ignores=[]),
                     "format_eta_extract", "exec"), ns)
        format_eta = ns["format_eta"]

        self.assertEqual(format_eta(0.0), "—",
                         "format_eta(0.0) must render as '—' — this is the "
                         "contract the warm-up emission relies on.")
        # Sanity: a positive ETA renders as a time, not "—".
        self.assertNotEqual(format_eta(90.0), "—")


if __name__ == "__main__":
    unittest.main(verbosity=2)
