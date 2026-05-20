"""Package entry point for `python -m urlcheck`.

This thin shim delegates to `urlcheck.cli.main`. Keeping it minimal means
the CLI logic itself stays in `cli.py` where it can be unit-tested
without re-running the entire module on import.

Tests should import `urlcheck.cli.main` directly rather than spawning a
subprocess — the latter is slow and harder to assert against.
"""

from __future__ import annotations

import sys

from .cli import main


if __name__ == "__main__":
    sys.exit(main())
