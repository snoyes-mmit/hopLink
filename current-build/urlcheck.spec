# urlcheck.spec — PyInstaller spec for the URL Health Checker GUI.
#
# This file is the canonical build configuration. The build_tools/build.py
# helper invokes PyInstaller against this spec; running `pyinstaller
# urlcheck.spec` directly works too.
#
# Why a spec file (instead of a long command line):
#   - Spec files are reproducible — they live in source control and version
#     with the rest of the code.
#   - Spec files let us conditionally branch on platform (Windows .exe with
#     icon vs macOS .app bundle) without running two separate build commands.
#   - Spec files give us full control over hidden imports, data files, and
#     binary excludes, which command-line flags do awkwardly.
#
# Build modes (controlled by env vars set by build.py):
#   URLCHECK_MODE   = "onedir" (default) | "onefile"
#   URLCHECK_DEBUG  = "1" to keep the console / produce a debug build
#
# Reference for one-file vs one-dir tradeoffs:
#   - onedir  -> faster startup, easier troubleshooting, antivirus-friendlier.
#   - onefile -> single .exe but extracts to a temp dir at launch, ~2-5 s
#                slower start, occasionally flagged by AV.

# noqa: E501 - long lines acceptable in spec config

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import (  # type: ignore[import]
    collect_data_files,
    collect_submodules,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

APP_NAME = "URL Health Checker"
# Internal short name used for the executable / .app folder. No spaces so
# Windows command line and macOS Finder both behave nicely.
EXE_NAME = "urlcheck"
ENTRY_SCRIPT = "app.py"

# Paths are relative to this spec file's directory at PyInstaller invocation
# time. SPECPATH is a PyInstaller-injected global.
PROJECT_ROOT = Path(SPECPATH).resolve()  # type: ignore[name-defined]

MODE = os.environ.get("URLCHECK_MODE", "onedir").lower()
DEBUG = os.environ.get("URLCHECK_DEBUG") == "1"

if MODE not in ("onedir", "onefile"):
    raise SystemExit(f"URLCHECK_MODE must be onedir or onefile, got {MODE!r}")

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

# ---------------------------------------------------------------------------
# Hidden imports
# ---------------------------------------------------------------------------
# PyInstaller's static analysis catches most imports, but a few things slip
# through:
#   - aiohttp uses dynamic imports for SSL contexts; collecting all of its
#     submodules is the safest way to avoid runtime ImportErrors on TLS.
#   - openpyxl loads worksheet readers lazily; collect_submodules guards us.
#   - asyncio.* and concurrent.futures are stdlib but referenced through
#     selectors that can confuse the analyzer on some platforms.

hiddenimports: list[str] = []
hiddenimports += collect_submodules("aiohttp")
hiddenimports += collect_submodules("aiosignal")
hiddenimports += collect_submodules("attrs")
hiddenimports += collect_submodules("multidict")
hiddenimports += collect_submodules("yarl")
hiddenimports += collect_submodules("frozenlist")
hiddenimports += collect_submodules("openpyxl")
# Explicitly include cert-handling stdlib modules that aiohttp pulls in via
# ssl.create_default_context. Belt-and-braces; PyInstaller usually finds
# these but we've seen frozen apps fail on TLS without them.
hiddenimports += [
    "ssl",
    "_ssl",
    "certifi",  # pulled in by aiohttp on some installs
]

# ---------------------------------------------------------------------------
# Data files
# ---------------------------------------------------------------------------
# certifi (if installed) ships ca-bundle.pem inside the package; we collect
# it explicitly so the frozen app can verify TLS certs without relying on
# the OS trust store. On macOS in particular, the system Python's CA bundle
# is not always present in a frozen build.

datas: list[tuple[str, str]] = []
try:
    datas += collect_data_files("certifi")
except Exception:
    # certifi is optional; aiohttp falls back to the system trust store.
    pass

# Include any project-level resources we might want to ship.
# We bundle the entire build_tools/assets/ folder so any icon files the
# user drops there are picked up automatically by gui/icon.py at runtime.
assets_dir = PROJECT_ROOT / "build_tools" / "assets"
if assets_dir.exists():
    for asset in assets_dir.iterdir():
        if asset.is_file() and asset.suffix.lower() in {".ico", ".icns", ".png"}:
            datas.append((str(asset), "."))

# ---------------------------------------------------------------------------
# Excludes — modules we deliberately strip out to shrink the bundle
# ---------------------------------------------------------------------------
# PyInstaller pulls in everything reachable from imports. Tkinter especially
# bloats the install on macOS; we never use it.

excludes = [
    "tkinter",
    "test",            # CPython's test package
    "unittest.test",
    "lib2to3",
    "pydoc",
    "doctest",
]

# ---------------------------------------------------------------------------
# Icon resolution
# ---------------------------------------------------------------------------
# Icons are optional. If the user drops an icon.ico (Windows) or icon.icns
# (macOS) in build_tools/assets/, we use it; otherwise PyInstaller uses its
# own default. We do NOT fail the build over a missing icon.

icon_file = None
if IS_WIN:
    candidate = assets_dir / "icon.ico"
    if candidate.exists():
        icon_file = str(candidate)
elif IS_MAC:
    candidate = assets_dir / "icon.icns"
    if candidate.exists():
        icon_file = str(candidate)

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

a = Analysis(  # type: ignore[name-defined]
    [str(PROJECT_ROOT / ENTRY_SCRIPT)],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)  # type: ignore[name-defined]

# ---------------------------------------------------------------------------
# Executable / Bundle assembly
# ---------------------------------------------------------------------------
# Common kwargs reused for EXE() across both build modes. Console=False
# means no terminal window pops up alongside the GUI on Windows.

common_exe_kwargs = dict(
    name=EXE_NAME,
    debug=DEBUG,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,         # UPX compression makes Windows Defender twitchy.
    console=DEBUG,     # Hide console for release builds.
    disable_windowed_traceback=False,
    argv_emulation=IS_MAC,  # macOS needs this for drag-onto-app file open.
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

if MODE == "onefile":
    # One file: everything (binaries + datas) is packed inside the EXE which
    # extracts to a temp dir on launch.
    exe = EXE(  # type: ignore[name-defined]
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        upx_exclude=[],
        runtime_tmpdir=None,
        **common_exe_kwargs,
    )
    # On macOS, also wrap the one-file binary in a .app bundle so it can be
    # double-clicked from Finder.
    if IS_MAC:
        app = BUNDLE(  # type: ignore[name-defined]
            exe,
            name=f"{APP_NAME}.app",
            icon=icon_file,
            bundle_identifier="com.urlcheck.urlcheck",
            info_plist={
                "CFBundleName": APP_NAME,
                "CFBundleDisplayName": APP_NAME,
                "CFBundleVersion": "0.5.0",
                "CFBundleShortVersionString": "0.5.0",
                "NSHighResolutionCapable": True,
                # Mark as a regular GUI app (not a daemon).
                "LSUIElement": False,
            },
        )

else:
    # One-dir: EXE references external dependencies, then COLLECT bundles
    # the EXE + binaries + datas into dist/<name>/.
    exe = EXE(  # type: ignore[name-defined]
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        **common_exe_kwargs,
    )
    coll = COLLECT(  # type: ignore[name-defined]
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=EXE_NAME,
    )
    # macOS .app bundle wrapping for onedir mode too.
    if IS_MAC:
        app = BUNDLE(  # type: ignore[name-defined]
            coll,
            name=f"{APP_NAME}.app",
            icon=icon_file,
            bundle_identifier="com.urlcheck.urlcheck",
            info_plist={
                "CFBundleName": APP_NAME,
                "CFBundleDisplayName": APP_NAME,
                "CFBundleVersion": "0.5.0",
                "CFBundleShortVersionString": "0.5.0",
                "NSHighResolutionCapable": True,
                "LSUIElement": False,
            },
        )
