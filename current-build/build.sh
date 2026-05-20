#!/usr/bin/env bash
# build.sh — macOS/Linux wrapper for build_tools/build.py
# Usage: ./build.sh [--mode onedir|onefile] [--debug] [--clean]

set -euo pipefail

# Move to the script's own directory so relative paths in build.py work
# regardless of where this script is invoked from.
cd "$(dirname "$0")"

# Prefer python3; fall back to python only if it is in fact Python 3.
if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    echo "Error: neither python3 nor python found on PATH." >&2
    exit 1
fi

exec "$PYTHON" build_tools/build.py "$@"
