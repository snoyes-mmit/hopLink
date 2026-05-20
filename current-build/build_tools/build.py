"""build.py — driver for packaging the URL Health Checker.

Runs PyInstaller against urlcheck.spec with mode/debug controls, sane
cleanups, and platform-aware output.

Usage:
    python build_tools/build.py                  # onedir (default)
    python build_tools/build.py --mode onefile
    python build_tools/build.py --mode onedir --debug
    python build_tools/build.py --clean          # rm -rf build/ dist/

What the build produces:
    onedir on Windows  ->  dist/urlcheck/urlcheck.exe        (+ a folder of DLLs)
    onefile on Windows ->  dist/urlcheck.exe                 (single file)
    onedir on macOS    ->  dist/URL Health Checker.app       (+ dist/urlcheck/)
    onefile on macOS   ->  dist/URL Health Checker.app       (single binary inside)
    onedir on Linux    ->  dist/urlcheck/urlcheck            (+ deps folder)
    onefile on Linux   ->  dist/urlcheck                     (single file)

Linux is supported as a side effect — the spec produces a working binary
there too, but distribution to Linux end users is out of scope for the
project.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# This script lives at <project>/build_tools/build.py — go up one level for
# the project root.
ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = ROOT / "urlcheck.spec"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build the URL Health Checker as a standalone app.",
    )
    p.add_argument(
        "--mode",
        choices=["onedir", "onefile"],
        default="onedir",
        help="Build mode (default: onedir — faster startup, easier to debug).",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="Build with console window + verbose output (Windows shows a "
             "terminal alongside the GUI).",
    )
    p.add_argument(
        "--clean",
        action="store_true",
        help="Remove build/ and dist/ before building.",
    )
    p.add_argument(
        "--no-confirm",
        action="store_true",
        help="Pass --noconfirm to PyInstaller (overwrite without asking).",
    )
    return p.parse_args()


def check_environment() -> None:
    """Fail fast with a friendly message if required deps are missing."""
    missing: list[str] = []
    for mod, hint in (
        ("PyInstaller", "pip install pyinstaller"),
        ("PySide6", "pip install PySide6"),
        ("aiohttp", "pip install aiohttp"),
        ("openpyxl", "pip install openpyxl"),
    ):
        try:
            __import__(mod)
        except ImportError:
            missing.append(f"  {mod}  →  {hint}")
    if missing:
        sys.stderr.write(
            "Missing build dependencies:\n" + "\n".join(missing) + "\n\n"
            "Install them all in one go:\n"
            "    pip install pyinstaller PySide6 aiohttp openpyxl certifi\n"
        )
        sys.exit(2)

    if not SPEC_FILE.exists():
        sys.stderr.write(f"Spec file not found: {SPEC_FILE}\n")
        sys.exit(2)


def clean_build_artifacts() -> None:
    for sub in ("build", "dist"):
        path = ROOT / sub
        if path.exists():
            print(f"Removing {path}")
            shutil.rmtree(path, ignore_errors=True)


def run_pyinstaller(mode: str, debug: bool, no_confirm: bool) -> int:
    """Invoke PyInstaller with the right env vars for our spec file."""
    env = os.environ.copy()
    env["URLCHECK_MODE"] = mode
    if debug:
        env["URLCHECK_DEBUG"] = "1"

    cmd = [sys.executable, "-m", "PyInstaller", str(SPEC_FILE)]
    if no_confirm:
        cmd.append("--noconfirm")
    if debug:
        cmd += ["--log-level", "DEBUG"]

    print()
    print(f"Building: mode={mode}, debug={debug}, platform={platform.system()}")
    print(f"Command : {' '.join(cmd)}")
    print(f"Env     : URLCHECK_MODE={env['URLCHECK_MODE']}"
          + (" URLCHECK_DEBUG=1" if debug else ""))
    print()

    # cwd MUST be the project root so SPECPATH resolves correctly.
    return subprocess.call(cmd, cwd=str(ROOT), env=env)


def report_outputs(mode: str) -> None:
    dist = ROOT / "dist"
    if not dist.exists():
        print()
        print("Build did not produce a dist/ directory. Check the log above.")
        return

    print()
    print("=" * 60)
    print("Build artifacts:")
    for child in sorted(dist.iterdir()):
        size = _human_size(_path_size(child))
        kind = "directory" if child.is_dir() else "file"
        print(f"  {child.name:40s}  {kind:9s}  {size}")
    print("=" * 60)
    print()

    sysname = platform.system()
    if sysname == "Darwin":
        app_bundle = next(dist.glob("*.app"), None)
        if app_bundle:
            print(f"Run with: open '{app_bundle}'")
            print(f"Distribute by zipping or DMG-ing this .app.")
    elif sysname == "Windows":
        if mode == "onefile":
            print("Run by double-clicking dist/urlcheck.exe")
        else:
            print("Run by double-clicking dist/urlcheck/urlcheck.exe")
            print("Distribute by zipping the entire dist/urlcheck/ folder.")
    else:  # Linux
        if mode == "onefile":
            print("Run by executing dist/urlcheck")
        else:
            print("Run by executing dist/urlcheck/urlcheck")


def _path_size(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    total = 0
    for child in p.rglob("*"):
        if child.is_file():
            try:
                total += child.stat().st_size
            except OSError:
                pass
    return total


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def main() -> int:
    args = parse_args()
    check_environment()
    if args.clean:
        clean_build_artifacts()
    rc = run_pyinstaller(args.mode, args.debug, args.no_confirm)
    if rc == 0:
        report_outputs(args.mode)
    else:
        print(f"\nBuild failed (exit code {rc}).")
    return rc


if __name__ == "__main__":
    sys.exit(main())
