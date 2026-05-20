"""Behavioral tests for the CLI entry point and `urlcheck` public API.

The CLI was previously unreachable: `python -m urlcheck …` failed with
`No module named urlcheck.__main__`, and `python cli.py` failed with a
relative-import error. The fix moved `cli.py` into the package and added
a `urlcheck/__main__.py` shim. These tests guard against any future
regression that breaks the entry point again.

Run with:
    python -m unittest tests.test_cli_entry -v
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import unittest
import unittest.mock
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_XLSX = ROOT / "tests" / "fixtures" / "sample_report.xlsx"


# ---------------------------------------------------------------------------
# Subprocess test: `python -m urlcheck --help`
# ---------------------------------------------------------------------------

class PythonDashMEntryPoint(unittest.TestCase):
    """Confirm the documented invocation actually runs.

    Uses subprocess so we exercise the real entry-point wiring
    (`urlcheck/__main__.py` being discovered as the module's `__main__`).
    If `__main__.py` is ever deleted, this test fails immediately.
    """

    def _run(self, *args: str, timeout: float = 15.0) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "urlcheck", *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            # Inherit PATH and PYTHONPATH from the parent so the child
            # finds the same Python environment we're running under.
            env=os.environ.copy(),
        )

    def test_module_dash_m_help_exits_zero(self):
        result = self._run("--help")
        self.assertEqual(
            result.returncode, 0,
            f"`python -m urlcheck --help` should exit 0.\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_module_dash_m_help_shows_usage(self):
        result = self._run("--help")
        # argparse always writes "usage:" at the top of --help output.
        self.assertIn("usage:", result.stdout.lower())
        # And the program name should be the package name, not "cli.py".
        self.assertIn("urlcheck", result.stdout)

    def test_module_dash_m_no_args_exits_nonzero_with_friendly_error(self):
        """Invoking with no args/input should error out with a helpful
        message, not a Python traceback.
        """
        result = self._run()
        self.assertNotEqual(result.returncode, 0)
        # The output should not contain a Python traceback header.
        combined = result.stdout + result.stderr
        self.assertNotIn(
            "Traceback (most recent call last)", combined,
            "CLI must not leak a traceback when given no input. "
            "Output was:\n" + combined,
        )


# ---------------------------------------------------------------------------
# In-process: urlcheck.cli.main is callable
# ---------------------------------------------------------------------------

class CliMainInProcess(unittest.TestCase):
    """Faster than subprocess and gives better failure diagnostics.

    Calls `urlcheck.cli.main(argv)` directly and intercepts SystemExit
    raised by argparse on `--help`.
    """

    def _run_main_capturing_exit(self, argv):
        """Call cli.main with given argv; return (exit_code, stdout, stderr).

        argparse calls sys.exit() on --help and on errors, which raises
        SystemExit. We intercept that and grab the captured streams.
        """
        from urlcheck.cli import main

        captured_out = io.StringIO()
        captured_err = io.StringIO()
        with unittest.mock.patch.object(sys, "stdout", captured_out), \
             unittest.mock.patch.object(sys, "stderr", captured_err):
            try:
                rc = main(argv)
            except SystemExit as e:
                rc = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        return rc, captured_out.getvalue(), captured_err.getvalue()

    def test_main_help_returns_zero(self):
        rc, out, err = self._run_main_capturing_exit(["--help"])
        self.assertEqual(rc, 0, f"--help should exit 0; got {rc}.\n{out}\n{err}")
        self.assertIn("usage:", out.lower())

    def test_main_signature(self):
        """`main(argv=None) -> int` so __main__.py and tests can call it."""
        import inspect
        from urlcheck.cli import main
        sig = inspect.signature(main)
        params = list(sig.parameters.values())
        self.assertEqual(len(params), 1, "main() should accept exactly one argument")
        self.assertEqual(params[0].name, "argv")

    @unittest.skipUnless(FIXTURE_XLSX.exists(),
                         f"fixture missing: {FIXTURE_XLSX}")
    def test_detect_only_mode_runs_without_aiohttp(self):
        """`--detect-only` is the path that doesn't need aiohttp.

        This is the most important end-to-end guarantee for the CLI: a
        user without aiohttp installed can still preview what would be
        checked, which the README documents as a feature.
        """
        rc, out, err = self._run_main_capturing_exit([
            "--excel", str(FIXTURE_XLSX),
            "--detect-only",
        ])
        self.assertEqual(rc, 0,
                         f"detect-only should exit 0.\nstdout:\n{out}\nstderr:\n{err}")
        # Output must include at least one URL extracted from the fixture.
        self.assertIn("https://", out)


# ---------------------------------------------------------------------------
# __main__.py file presence (regression guard)
# ---------------------------------------------------------------------------

class MainModulePresent(unittest.TestCase):
    """If `urlcheck/__main__.py` is ever deleted, `python -m urlcheck`
    silently breaks again. This file-presence check is the cheapest
    regression guard available.
    """

    def test_main_module_file_exists(self):
        main_py = ROOT / "urlcheck" / "__main__.py"
        self.assertTrue(
            main_py.is_file(),
            f"urlcheck/__main__.py is missing. Without it, "
            f"`python -m urlcheck …` fails with "
            f"'No module named urlcheck.__main__'.",
        )

    def test_main_module_imports_cli_main(self):
        """The shim must wire to `cli.main` — otherwise it does nothing."""
        src = (ROOT / "urlcheck" / "__main__.py").read_text(encoding="utf-8")
        # Don't pin exact text; just confirm the wiring.
        self.assertIn("from .cli import main", src)
        self.assertIn("main()", src)

    def test_cli_module_is_inside_package(self):
        """cli.py must live inside urlcheck/, not at project root.

        If a future refactor moves it back, relative imports break and
        the CLI becomes unreachable again. This catches that.
        """
        self.assertTrue((ROOT / "urlcheck" / "cli.py").is_file())
        self.assertFalse(
            (ROOT / "cli.py").is_file(),
            "cli.py at project root would have relative-import issues. "
            "It belongs in urlcheck/cli.py.",
        )


# ---------------------------------------------------------------------------
# Public API: `from urlcheck import …`
# ---------------------------------------------------------------------------

class PublicApiExports(unittest.TestCase):
    """The package-level public API documented in __init__.py / README."""

    def test_eager_symbols_importable(self):
        """These three are lightweight and should always be available."""
        from urlcheck import Classification, Settings, UrlCheckResult
        # Smoke check each one exists and is the right kind of thing.
        self.assertTrue(hasattr(Classification, "OK"))
        self.assertTrue(callable(Settings))
        self.assertTrue(callable(UrlCheckResult))

    def test_dunder_all_lists_documented_names(self):
        import urlcheck
        # Spot-check that __all__ is set and contains the eager + lazy names.
        self.assertIn("Classification", urlcheck.__all__)
        self.assertIn("Settings", urlcheck.__all__)
        self.assertIn("UrlCheckResult", urlcheck.__all__)
        self.assertIn("check_urls", urlcheck.__all__)
        self.assertIn("check_urls_sync", urlcheck.__all__)

    def test_unknown_attribute_raises_attribute_error(self):
        """`urlcheck.does_not_exist` must raise AttributeError, not
        ImportError or something weirder. This is what PEP 562 expects
        and what `hasattr` / `getattr(..., default)` rely on.
        """
        import urlcheck
        with self.assertRaises(AttributeError):
            urlcheck.does_not_exist  # noqa: B018 - intentional access

    def test_hasattr_negative_works(self):
        """`hasattr(urlcheck, 'nope')` must be False, not crash.

        This is the practical consequence of `__getattr__` correctly
        raising AttributeError for unknown names.
        """
        import urlcheck
        self.assertFalse(hasattr(urlcheck, "does_not_exist"))

    def test_check_urls_is_lazy(self):
        """Importing the package must NOT eagerly load aiohttp.

        The CLI's `--detect-only` mode and the Excel-only programmatic
        path are documented to work without aiohttp installed. If
        `import urlcheck` pulled it in, that contract would silently
        break the moment someone removed aiohttp from their venv.
        """
        # Use a subprocess so we can guarantee a fresh import state.
        # Pulling `sys.modules` snapshots within one process can be
        # polluted by earlier tests that already imported the engine.
        code = (
            "import urlcheck; "
            "import sys; "
            "assert 'aiohttp' not in sys.modules, "
            "'aiohttp was imported by `import urlcheck`'; "
            "print('OK')"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=10,
            env=os.environ.copy(),
        )
        self.assertEqual(
            result.returncode, 0,
            f"Subprocess failed:\nstdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}",
        )
        self.assertIn("OK", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
