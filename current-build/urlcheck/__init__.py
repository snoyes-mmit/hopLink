"""Public API for the `urlcheck` package.

The lightweight symbols (`Classification`, `Settings`, `UrlCheckResult`)
are imported eagerly because they have no expensive dependencies.

The heavier symbols (`check_urls`, `check_urls_sync`) live in `engine`,
which imports `aiohttp` at module top. We expose them via PEP 562
`__getattr__` so that `import urlcheck` doesn't pull in aiohttp
unconditionally — callers using only the Excel layer (e.g.
`--detect-only` mode in the CLI, or programmatic extraction without
HTTP) can run without aiohttp installed.

Usage:

    from urlcheck import check_urls, Settings, Classification

    results = await check_urls(
        ["https://example.com"],
        settings=Settings(concurrency=10, timeout=15.0),
    )
    for r in results:
        if r.classification != Classification.OK:
            print(r.original_url, r.error_detail)
"""

from __future__ import annotations

from .models import Classification, Settings, UrlCheckResult

__all__ = [
    "Classification",
    "Settings",
    "UrlCheckResult",
    "check_urls",
    "check_urls_sync",
]


def __getattr__(name: str):
    """Lazy re-export of engine symbols.

    Deferred so that merely importing `urlcheck` doesn't require aiohttp.
    The first access to `urlcheck.check_urls` will import the engine
    module (which in turn imports aiohttp); subsequent accesses are
    cached on this module's namespace by the standard import machinery.
    """
    if name in ("check_urls", "check_urls_sync"):
        from . import engine
        return getattr(engine, name)
    raise AttributeError(f"module 'urlcheck' has no attribute {name!r}")
