"""Application-icon resolution for both dev and frozen (PyInstaller) runs.

PyInstaller exposes bundled data files at runtime through `sys._MEIPASS`
(onefile) or alongside the executable (onedir). We probe both, plus the
source layout for `python app.py` runs.

If no icon file can be found, we fall back to a small embedded SVG —
better an OK-looking generic icon than a Python-default missing-file
glyph in the user's taskbar.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QPixmap


# Embedded fallback: a simple "link" glyph as SVG. Tiny, scales nicely at
# any DPI, no external dependencies. Used only if no .ico/.png is found.
_FALLBACK_SVG = b"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="10" fill="#305496"/>
  <g fill="none" stroke="#ffffff" stroke-width="4" stroke-linecap="round">
    <path d="M22 32 L42 32"/>
    <path d="M28 24 a8 8 0 0 0 0 16 h4"/>
    <path d="M36 24 a8 8 0 0 1 0 16 h-4" transform="translate(0 0)"/>
  </g>
</svg>
"""


# Files / directories whose presence identifies the project root in a dev
# checkout. We walk upward from this module's path until one of these is
# found. Listed in priority order — the spec file is the strongest signal
# because it exists only at root and only in this project, while
# `pyproject.toml` is a defensive future-proofing entry in case the build
# layout ever switches to one.
_ROOT_MARKERS: tuple[str, ...] = (
    "urlcheck.spec",
    "pyproject.toml",
    "build_tools",
    "app.py",
)


def _find_project_root(start: Path) -> Optional[Path]:
    """Walk upward from `start` looking for a project-root marker.

    Returns the first directory that contains any of `_ROOT_MARKERS`, or
    `None` if we reach the filesystem root without finding one. Robust to
    refactors that move this module deeper or shallower in the package
    tree — the previous `parents[2]` approach silently pointed at the
    wrong directory whenever the layout changed by even one level.

    `start` is expected to be a resolved (absolute) Path; the caller
    passes `Path(__file__).resolve()`.
    """
    # Start with the file's *parent* — `start` itself is the file, not a
    # directory to scan. `Path.parents` is finite even for the filesystem
    # root, so this loop terminates.
    for candidate in start.parents:
        for marker in _ROOT_MARKERS:
            if (candidate / marker).exists():
                return candidate
    return None


def _candidate_paths() -> list[Path]:
    """Return possible locations for the app icon, in priority order."""
    candidates: list[Path] = []

    # 1) Frozen build: PyInstaller's _MEIPASS for onefile, or the dir
    #    containing the executable for onedir. In a frozen build,
    #    walking upward from __file__ would land somewhere inside the
    #    PyInstaller staging dir — useless — so we skip step 2 entirely
    #    when frozen.
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass))
        candidates.append(Path(sys.executable).parent)
    else:
        # 2) Dev layout: <project>/build_tools/assets/ — resolved via a
        #    marker-based walk so it survives refactors that move this
        #    file in the package tree.
        here = Path(__file__).resolve()
        project_root = _find_project_root(here)
        if project_root is not None:
            candidates.append(project_root / "build_tools" / "assets")
        # If we found no marker (e.g. the package was installed via pip
        # into site-packages with the build tree stripped), we just skip
        # this candidate. The embedded SVG fallback in load_app_icon()
        # handles "nothing found" gracefully.

    # 3) Current working directory — last-resort fallback.
    candidates.append(Path.cwd())

    return candidates


def _find_icon_file() -> Optional[Path]:
    """Probe for an icon file in known locations. Tries .ico, .png, .icns
    in that order, since QIcon handles all three on every platform.
    """
    names = ("icon.ico", "icon.png", "icon.icns")
    for d in _candidate_paths():
        if not d.is_dir():
            continue
        for name in names:
            p = d / name
            if p.is_file():
                return p
    return None


def load_app_icon() -> QIcon:
    """Return a QIcon ready to apply to the app and main window.

    Always returns a non-null QIcon, even if no file was found (uses the
    embedded SVG fallback).
    """
    path = _find_icon_file()
    if path is not None:
        icon = QIcon(str(path))
        if not icon.isNull():
            return icon

    # Fallback: build from embedded SVG.
    pixmap = QPixmap()
    pixmap.loadFromData(QByteArray(_FALLBACK_SVG), "SVG")
    return QIcon(pixmap)
