"""Minimal structural smoke test for the GUI package.

This file is the *only* test that uses source-text or AST inspection. It
exists for a narrow purpose: confirming the GUI package's file layout is
intact and that the modules don't accidentally shadow stdlib names. It
deliberately does NOT verify behaviors via grepped strings — for that,
see the behavior-focused test files:

    tests/test_url_normalize.py    — URL parsing/normalization
    tests/test_signatures.py        — bot-protection detection
    tests/test_excel_output.py     — Report writer (incl. golden fixture)
    tests/test_integration.py       — End-to-end extract→write pipeline

The original `test_phase4.py` and `test_phase6.py` files were AST-grep
tests that asserted strings like `"Checking…"` appeared in source code;
they passed when behavior was broken and failed during innocent refactors.
They have been superseded by the four files above.
"""

from __future__ import annotations

import unittest
from pathlib import Path

# Project root: tests/ is a sibling of urlcheck/.
ROOT = Path(__file__).resolve().parent.parent
GUI_DIR = ROOT / "urlcheck" / "gui"


class GuiPackageLayout(unittest.TestCase):
    """The GUI package must contain its expected modules.

    These are smoke checks — they fail loudly if a module is renamed,
    moved, or accidentally deleted. They do NOT assert anything about
    module contents.
    """

    EXPECTED_MODULES = (
        "applog.py",
        "icon.py",
        "main_window.py",
        "settings.py",
        "signals.py",
        "widgets.py",
        "worker.py",
    )

    def test_all_expected_modules_present(self):
        for name in self.EXPECTED_MODULES:
            path = GUI_DIR / name
            self.assertTrue(path.is_file(),
                            f"GUI module missing: {path}")

    def test_no_logging_py_shadowing_stdlib(self):
        """`applog.py` was named specifically to avoid shadowing stdlib `logging`.

        If a future contributor renames it back to `logging.py`, every
        `import logging` inside the package would resolve to the local
        module instead of the standard library. This test guards against
        that mistake.
        """
        rogue = GUI_DIR / "logging.py"
        self.assertFalse(
            rogue.exists(),
            "urlcheck/gui/logging.py would shadow Python's stdlib logging "
            "module — rename it to applog.py or similar.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
