"""Behavioral tests for the project-root lookup in `urlcheck.gui.icon`.

Covers:
  - `_find_project_root` finds the root by markers, regardless of the
    file's depth in the package tree (the regression we're fixing).
  - The lookup walks upward until a marker is found, or returns None
    when nothing matches.
  - `_candidate_paths` includes the dev-layout candidate when not
    frozen, AND skips it when frozen (where the walk would land
    inside PyInstaller's staging dir).
  - The frozen-build branch still adds `_MEIPASS` and executable dir.

PySide6 is stubbed at import time so tests run anywhere.

Run with:
    python -m unittest tests.test_icon_root_lookup -v
"""

from __future__ import annotations

import sys
import tempfile
import types
import unittest
import unittest.mock
from pathlib import Path


# ---------------------------------------------------------------------------
# PySide6 stub
# ---------------------------------------------------------------------------

def _install_pyside6_stub() -> None:
    """icon.py imports QByteArray, QIcon, QPixmap. Stub them out."""
    if "PySide6" in sys.modules and hasattr(
        sys.modules.get("PySide6.QtGui"), "QIcon"
    ):
        return

    pyside6 = sys.modules.get("PySide6") or types.ModuleType("PySide6")
    qtcore = sys.modules.get("PySide6.QtCore") or types.ModuleType("PySide6.QtCore")
    qtgui = types.ModuleType("PySide6.QtGui")

    # Minimal QByteArray that accepts bytes and exposes the payload.
    class _QByteArrayStub:
        def __init__(self, data: bytes = b""):
            self._data = bytes(data)

    # Minimal QIcon: tracks whether it was loaded from a real file.
    class _QIconStub:
        def __init__(self, source=None):
            self._source = source
            # Treat string-path icons as "non-null" if the file exists,
            # else null. Pixmap-based icons are always non-null in tests.
            self._null = (
                isinstance(source, str) and not Path(source).is_file()
            )

        def isNull(self) -> bool:  # noqa: N802 - mirror Qt camelCase
            return self._null

    class _QPixmapStub:
        def __init__(self):
            self._has_data = False

        def loadFromData(self, _data, _format=None):  # noqa: N802
            self._has_data = True
            return True

    qtcore.QByteArray = _QByteArrayStub
    qtgui.QIcon = _QIconStub
    qtgui.QPixmap = _QPixmapStub
    pyside6.QtCore = qtcore
    pyside6.QtGui = qtgui

    sys.modules["PySide6"] = pyside6
    sys.modules["PySide6.QtCore"] = qtcore
    sys.modules["PySide6.QtGui"] = qtgui


_install_pyside6_stub()

# Now safe to import the module under test.
from urlcheck.gui import icon as icon_mod  # noqa: E402


# ---------------------------------------------------------------------------
# _find_project_root: marker-based walk
# ---------------------------------------------------------------------------

class FindProjectRootByMarker(unittest.TestCase):
    """Each test builds a fake project layout in a tempdir and probes from
    a synthetic 'icon.py' location inside it.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def _place_file(self, *parts: str) -> Path:
        """Create an empty file at `root/parts/...` and return its path."""
        path = self.root.joinpath(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        return path

    def _place_dir(self, *parts: str) -> Path:
        """Create a directory at `root/parts/...` and return its path."""
        path = self.root.joinpath(*parts)
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ----- finding the root with each marker -----

    def test_finds_root_via_spec_file(self):
        """The canonical case: urlcheck.spec at the root."""
        self._place_file("urlcheck.spec")
        fake_icon = self._place_file("urlcheck", "gui", "icon.py")
        self.assertEqual(
            icon_mod._find_project_root(fake_icon),
            self.root,
        )

    def test_finds_root_via_build_tools_directory(self):
        """build_tools/ is a strong root marker even without urlcheck.spec."""
        self._place_dir("build_tools")
        fake_icon = self._place_file("urlcheck", "gui", "icon.py")
        self.assertEqual(
            icon_mod._find_project_root(fake_icon),
            self.root,
        )

    def test_finds_root_via_app_py(self):
        self._place_file("app.py")
        fake_icon = self._place_file("urlcheck", "gui", "icon.py")
        self.assertEqual(
            icon_mod._find_project_root(fake_icon),
            self.root,
        )

    def test_finds_root_via_pyproject_toml(self):
        """Future-proofing: works if the project ever adopts pyproject.toml."""
        self._place_file("pyproject.toml")
        fake_icon = self._place_file("urlcheck", "gui", "icon.py")
        self.assertEqual(
            icon_mod._find_project_root(fake_icon),
            self.root,
        )

    # ----- depth-invariant: the original bug -----

    def test_root_found_when_file_is_shallow(self):
        """If icon.py ever gets flattened to urlcheck/icon.py, the marker
        walk still finds the root. With the old `parents[2]`, this case
        would silently point one level too high.
        """
        self._place_file("urlcheck.spec")
        # One level less deep: urlcheck/icon.py (no gui/).
        fake_icon = self._place_file("urlcheck", "icon.py")
        self.assertEqual(
            icon_mod._find_project_root(fake_icon),
            self.root,
        )

    def test_root_found_when_file_is_deep(self):
        """If icon.py ever gets moved deeper (e.g. into a resources subpkg),
        the marker walk still finds the root.
        """
        self._place_file("urlcheck.spec")
        fake_icon = self._place_file(
            "urlcheck", "gui", "resources", "icon.py",
        )
        self.assertEqual(
            icon_mod._find_project_root(fake_icon),
            self.root,
        )

    def test_root_found_when_file_is_at_root_level(self):
        """Pathological: icon.py beside the spec itself."""
        self._place_file("urlcheck.spec")
        fake_icon = self._place_file("icon.py")
        self.assertEqual(
            icon_mod._find_project_root(fake_icon),
            self.root,
        )

    # ----- no markers anywhere -----

    def test_returns_none_when_no_marker_present(self):
        """A bare directory tree without any project markers should
        return None rather than guessing.
        """
        fake_icon = self._place_file("some", "deep", "tree", "icon.py")
        result = icon_mod._find_project_root(fake_icon)
        # The walk reaches the filesystem root without finding a marker.
        # We accept either None or any directory not under `self.root`
        # (a host filesystem with `app.py` at /tmp could shadow). To be
        # robust, we just assert it's not pointing into the wrong dir
        # inside our tempdir — if any of our intermediate parents had
        # accidentally been treated as root, that'd be the failure mode.
        for fake_intermediate in (
            fake_icon.parent,                            # tree/
            fake_icon.parent.parent,                     # deep/
            fake_icon.parent.parent.parent,              # some/
        ):
            self.assertNotEqual(
                result, fake_intermediate,
                f"Should not treat {fake_intermediate} as root — no marker",
            )

    # ----- picks the nearest marker -----

    def test_picks_nearest_marker_when_two_levels_match(self):
        """If a nested directory ALSO contains a marker (rare but possible
        in monorepos), the nearest one wins — we walk bottom-up and stop
        at the first hit.
        """
        # Outer project at self.root, inner "project" two levels down.
        self._place_file("urlcheck.spec")
        self._place_file("apps", "urlcheck", "app.py")
        fake_icon = self._place_file(
            "apps", "urlcheck", "urlcheck", "gui", "icon.py",
        )
        # The walk should stop at apps/urlcheck (which has app.py), not
        # at self.root (which has urlcheck.spec).
        self.assertEqual(
            icon_mod._find_project_root(fake_icon),
            self.root / "apps" / "urlcheck",
        )


# ---------------------------------------------------------------------------
# _candidate_paths: frozen vs dev branches
# ---------------------------------------------------------------------------

class CandidatePathsDevMode(unittest.TestCase):
    """When NOT frozen, the dev candidate uses the marker walk."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / "urlcheck.spec").write_text("", encoding="utf-8")
        # We need a fake icon.py inside the tempdir so __file__ resolves
        # under our marker tree.
        gui_dir = self.root / "urlcheck" / "gui"
        gui_dir.mkdir(parents=True)
        self.fake_icon = gui_dir / "icon.py"
        self.fake_icon.write_text("", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_dev_mode_includes_build_tools_assets(self):
        """Patch sys.frozen=False and icon.__file__ → confirm the dev
        candidate is `{root}/build_tools/assets`.
        """
        with unittest.mock.patch.object(icon_mod, "__file__", str(self.fake_icon)), \
             unittest.mock.patch.object(sys, "frozen", False, create=True):
            paths = icon_mod._candidate_paths()
        expected_assets = self.root / "build_tools" / "assets"
        self.assertIn(expected_assets, paths,
                      f"Expected {expected_assets} in {paths}")

    def test_dev_mode_skips_dev_candidate_when_no_marker(self):
        """If the marker walk returns None, _candidate_paths should still
        produce a sensible list (cwd at minimum) rather than crash.
        """
        # Put the fake icon somewhere that has NO marker above it. Use a
        # sibling tempdir so the walk can't reach our self.root markers.
        with tempfile.TemporaryDirectory() as other:
            other_path = Path(other).resolve()
            fake = other_path / "deep" / "icon.py"
            fake.parent.mkdir(parents=True)
            fake.write_text("", encoding="utf-8")
            with unittest.mock.patch.object(icon_mod, "__file__", str(fake)), \
                 unittest.mock.patch.object(sys, "frozen", False, create=True):
                paths = icon_mod._candidate_paths()
            # No assets candidate from a non-existent project root.
            self.assertFalse(
                any(p.name == "assets" for p in paths
                    if p.parent.name == "build_tools"),
                f"Should not invent a build_tools/assets path: {paths}",
            )
            # Still produces a non-empty list (cwd fallback).
            self.assertGreater(len(paths), 0)


class CandidatePathsFrozenMode(unittest.TestCase):
    """When frozen, the dev candidate is skipped entirely (walking upward
    from inside _MEIPASS would land in the staging dir, not the user's
    project)."""

    def test_frozen_mode_uses_meipass_and_exe_dir(self):
        with unittest.mock.patch.object(sys, "frozen", True, create=True), \
             unittest.mock.patch.object(sys, "_MEIPASS", "/fake/meipass", create=True), \
             unittest.mock.patch.object(sys, "executable", "/fake/exe/urlcheck"):
            paths = icon_mod._candidate_paths()
        # Both PyInstaller candidates must be present.
        self.assertIn(Path("/fake/meipass"), paths)
        self.assertIn(Path("/fake/exe"), paths)

    def test_frozen_mode_does_not_include_build_tools_assets(self):
        """Critical: walking upward from _MEIPASS doesn't yield a sensible
        project root, so we skip step 2 entirely when frozen.
        """
        with unittest.mock.patch.object(sys, "frozen", True, create=True), \
             unittest.mock.patch.object(sys, "_MEIPASS", "/fake/meipass", create=True), \
             unittest.mock.patch.object(sys, "executable", "/fake/exe/urlcheck"):
            paths = icon_mod._candidate_paths()
        # No build_tools/assets dir should appear — the dev branch is
        # disabled in frozen builds.
        self.assertFalse(
            any("build_tools" in str(p) for p in paths),
            f"Frozen build should not probe build_tools/assets: {paths}",
        )

    def test_frozen_mode_without_meipass_still_uses_exe_dir(self):
        """onedir builds set sys.frozen but not _MEIPASS."""
        with unittest.mock.patch.object(sys, "frozen", True, create=True), \
             unittest.mock.patch.object(sys, "executable", "/fake/exe/urlcheck"):
            # Remove _MEIPASS if present so the onefile branch is skipped.
            had_meipass = hasattr(sys, "_MEIPASS")
            saved = getattr(sys, "_MEIPASS", None)
            if had_meipass:
                delattr(sys, "_MEIPASS")
            try:
                paths = icon_mod._candidate_paths()
            finally:
                if had_meipass:
                    sys._MEIPASS = saved  # type: ignore[attr-defined]
        self.assertIn(Path("/fake/exe"), paths)


# ---------------------------------------------------------------------------
# Regression guard: parents[2] is gone
# ---------------------------------------------------------------------------

class NoParentsCountedManually(unittest.TestCase):
    """Belt-and-braces: confirm icon.py doesn't use `.parents[<int>]` to
    locate the project root. If a future refactor reintroduces that
    pattern, this fails loudly.
    """

    def test_no_parents_index_in_module_source(self):
        src = Path(icon_mod.__file__).read_text(encoding="utf-8")
        # We look for `parents[` followed by a digit — the brittle pattern.
        # If a comment ever needs the literal phrase, we'd need to allow
        # it, but right now there is no legitimate use of indexed parents
        # in this file.
        import re
        match = re.search(r"\.parents\[\s*\d+\s*\]", src)
        self.assertIsNone(
            match,
            f"icon.py reintroduced a brittle `.parents[N]` index: {match!r}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
