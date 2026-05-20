"""Command-line interface for the URL checker.

Examples:
    # Plain URLs
    python -m urlcheck https://example.com https://example.org
    python -m urlcheck --input urls.txt --concurrency 50 --timeout 15
    python -m urlcheck --input urls.txt --output results.json --format json

    # Excel input (Phase 2)
    python -m urlcheck --excel links.xlsx
    python -m urlcheck --excel links.xlsx --sheet Links --column URL
    python -m urlcheck --excel links.xlsx --sheet Sheet1 --column B --header-row 1
    python -m urlcheck --excel links.xlsx --column 3 --output results.json
    python -m urlcheck --excel links.xlsx --detect-only      # preview, no checking
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Iterable, Optional

from .models import Classification, Settings, UrlCheckResult


# Lazy engine import so --excel --detect-only works without aiohttp installed.
def _import_engine():
    from .engine import check_urls_sync  # noqa: WPS433 (intentional local import)
    return check_urls_sync


# ---------------------------------------------------------------------------
# Plain text input
# ---------------------------------------------------------------------------

def _read_urls_from_file(path: Path) -> list[str]:
    """Read URLs from a text file, one per line, ignoring blanks and # comments."""
    urls: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)
    return urls


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="urlcheck",
        description="Async URL health checker (engine + Excel input layer).",
    )
    # ---- Input sources ----
    p.add_argument(
        "urls",
        nargs="*",
        help="URLs to check (positional). Combined with --input/--excel if given.",
    )
    p.add_argument(
        "-i", "--input",
        type=Path,
        default=None,
        help="Path to a text file with one URL per line.",
    )

    # Excel input (Phase 2)
    excel_group = p.add_argument_group("Excel input")
    excel_group.add_argument(
        "--excel",
        type=Path,
        default=None,
        help="Path to an .xlsx file. Sheet/column auto-detected if not specified.",
    )
    excel_group.add_argument(
        "--sheet",
        type=str,
        default=None,
        help="Sheet name. If omitted, the best URL-y sheet is auto-picked.",
    )
    excel_group.add_argument(
        "--column",
        type=str,
        default=None,
        help="Column reference: letter (B), 1-based index (2), or header name (URL).",
    )
    excel_group.add_argument(
        "--header-row",
        type=int,
        default=1,
        help="Header row number (1-based). Use 0 to indicate no header. Default: 1.",
    )
    excel_group.add_argument(
        "--scan-rows",
        type=int,
        default=50,
        help="Rows to sample when auto-detecting URL columns (default: 50).",
    )
    excel_group.add_argument(
        "--auto-https",
        action="store_true",
        help="Promote bare domains (e.g. 'example.com') to https. Off by default.",
    )
    excel_group.add_argument(
        "--detect-only",
        action="store_true",
        help="Extract & print URLs and locations from Excel, but do not check them. "
             "Useful for previewing what will be checked.",
    )

    # ---- Engine settings ----
    engine_group = p.add_argument_group("Engine settings")
    engine_group.add_argument(
        "--concurrency", type=int, default=Settings.concurrency,
        help=f"Global concurrency cap (default: {Settings.concurrency}).",
    )
    engine_group.add_argument(
        "--per-domain-delay", type=float, default=Settings.per_domain_delay,
        help=f"Min seconds between requests to same domain "
             f"(default: {Settings.per_domain_delay}).",
    )
    engine_group.add_argument(
        "--timeout", type=float, default=Settings.timeout,
        help=f"Total request timeout in seconds (default: {Settings.timeout}).",
    )
    engine_group.add_argument(
        "--retries", type=int, default=Settings.retries,
        help=f"Retries per attempt (default: {Settings.retries}).",
    )
    engine_group.add_argument(
        "--max-redirects", type=int, default=Settings.max_redirects,
        help=f"Max redirects to follow (default: {Settings.max_redirects}).",
    )
    engine_group.add_argument(
        "--body-read-limit", type=int, default=Settings.body_read_limit,
        help=f"Max bytes of GET body to read for challenge detection "
             f"(default: {Settings.body_read_limit}).",
    )

    # ---- Output ----
    out_group = p.add_argument_group("Output")
    out_group.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Path to write results.",
    )
    out_group.add_argument(
        "-f", "--format", choices=["json", "csv", "xlsx"], default=None,
        help="Output format when --output is set. If omitted, format is "
             "inferred from --output's extension (.xlsx/.csv/.json), "
             "defaulting to xlsx when --excel is used, json otherwise.",
    )
    out_group.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-URL progress output.",
    )
    return p


# ---------------------------------------------------------------------------
# Settings + URL gathering
# ---------------------------------------------------------------------------

def _settings_from_args(args: argparse.Namespace) -> Settings:
    return replace(
        Settings(),
        concurrency=args.concurrency,
        per_domain_delay=args.per_domain_delay,
        timeout=args.timeout,
        retries=args.retries,
        max_redirects=args.max_redirects,
        body_read_limit=args.body_read_limit,
    )


def _gather_text_urls(args: argparse.Namespace) -> list[str]:
    """URLs from positional args + --input file (no Excel)."""
    urls: list[str] = list(args.urls or [])
    if args.input:
        if not args.input.exists():
            print(f"error: input file not found: {args.input}", file=sys.stderr)
            sys.exit(2)
        urls.extend(_read_urls_from_file(args.input))
    seen: set[str] = set()
    unique: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


# ---------------------------------------------------------------------------
# Excel flow
# ---------------------------------------------------------------------------

def _run_excel_extraction(args: argparse.Namespace):
    """Open the Excel file, resolve sheet+column, extract URLs.

    Returns an ExtractionResult. May exit on errors.
    """
    from .excel_input import (
        open_workbook, list_sheets, resolve_column,
        auto_pick_sheet_and_column, auto_pick_column,
        extract_urls,
    )
    from .url_normalize import NormalizationOptions

    if not args.excel.exists():
        print(f"error: Excel file not found: {args.excel}", file=sys.stderr)
        sys.exit(2)

    try:
        wb = open_workbook(args.excel)
    except (ValueError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(2)

    sheets = list_sheets(wb)
    if not sheets:
        print("error: workbook has no sheets", file=sys.stderr)
        sys.exit(2)

    header_row: Optional[int] = args.header_row if args.header_row >= 1 else None

    # ---- Resolve sheet ----
    sheet_name = args.sheet
    if sheet_name and sheet_name not in sheets:
        print(f"error: sheet {sheet_name!r} not found. Available: "
              f"{', '.join(sheets)}", file=sys.stderr)
        sys.exit(2)

    # ---- Resolve column ----
    if sheet_name and args.column:
        try:
            selection = resolve_column(wb, sheet_name, args.column, header_row=header_row)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            sys.exit(2)
    elif sheet_name and not args.column:
        sel = auto_pick_column(wb, sheet_name, args.scan_rows, header_row)
        if sel is None:
            print(f"error: no URL-like columns detected on sheet {sheet_name!r}. "
                  f"Specify --column explicitly.", file=sys.stderr)
            sys.exit(2)
        selection = sel
        if not args.quiet:
            print(f"Auto-picked column {selection.column_letter} "
                  f"(header={selection.header!r}) on sheet {sheet_name!r}.",
                  file=sys.stderr)
    elif args.column and not sheet_name:
        sheet_name = sheets[0]
        try:
            selection = resolve_column(wb, sheet_name, args.column, header_row=header_row)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            sys.exit(2)
        if not args.quiet:
            print(f"Using first sheet: {sheet_name!r}.", file=sys.stderr)
    else:
        sel = auto_pick_sheet_and_column(wb, args.scan_rows, header_row)
        if sel is None:
            print("error: no URL-like columns detected in any sheet. "
                  "Specify --sheet and --column.", file=sys.stderr)
            sys.exit(2)
        selection = sel
        if not args.quiet:
            print(f"Auto-picked: sheet={selection.sheet!r} "
                  f"column={selection.column_letter} (header={selection.header!r})",
                  file=sys.stderr)

    # ---- Extract ----
    norm_opts = NormalizationOptions(auto_https_for_bare_domains=args.auto_https)
    extraction = extract_urls(wb, selection, header_row=header_row, options=norm_opts)

    if not args.quiet:
        s = extraction.summary
        print(f"Extracted from {selection.sheet}!{selection.column_letter}: "
              f"scanned={s.total_cells_scanned} cells, "
              f"occurrences={s.total_occurrences}, "
              f"unique URLs={s.unique_urls}, "
              f"rejected={s.rejected_cells}",
              file=sys.stderr)
    return extraction


# ---------------------------------------------------------------------------
# Progress + output
# ---------------------------------------------------------------------------

def _make_progress_printer(total: int):
    state = {"last_print": 0.0, "ok": 0, "broken": 0, "blocked": 0}

    def cb(completed: int, total_: int, latest: UrlCheckResult) -> None:
        if latest.classification == Classification.OK:
            state["ok"] += 1
        elif latest.classification == Classification.BROKEN:
            state["broken"] += 1
        else:
            state["blocked"] += 1
        now = time.monotonic()
        if completed == total_ or (now - state["last_print"]) >= 0.1:
            state["last_print"] = now
            sys.stderr.write(
                f"\r[{completed:>6}/{total_}] "
                f"ok={state['ok']} broken={state['broken']} blocked={state['blocked']}    "
            )
            sys.stderr.flush()
            if completed == total_:
                sys.stderr.write("\n")
    return cb


def _write_json_simple(results: Iterable[UrlCheckResult], out: Path) -> None:
    payload = [r.to_dict() for r in results]
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_csv_simple(results: Iterable[UrlCheckResult], out: Path) -> None:
    fields = [
        "original_url", "final_url", "domain", "classification",
        "http_status", "error_detail", "likely_reason",
        "response_time_ms", "method_used", "attempts", "checked_at_utc",
    ]
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            row = r.to_dict()
            w.writerow({k: row.get(k, "") for k in fields})


def _write_json_with_locations(enriched, extraction, out: Path) -> None:
    """Phase 2 output: results enriched with cell locations.

    JSON shape: top-level object with extraction metadata + a `results` list
    of objects, each containing the engine's result fields plus
    `cell_locations` and `cell_occurrences`.
    """
    items = []
    for e in enriched:
        d = e.result.to_dict()
        d["cell_locations"] = e.locations
        d["cell_occurrences"] = [
            {
                "sheet": o.sheet,
                "cell": o.cell,
                "row": o.row,
                "col": o.col,
                "value": o.value,
                "hyperlink": o.hyperlink,
            }
            for o in e.occurrences
        ]
        items.append(d)
    payload = {
        "selection": {
            "sheet": extraction.selection.sheet,
            "column": extraction.selection.column,
            "column_letter": extraction.selection.column_letter,
            "header": extraction.selection.header,
        },
        "summary": {
            "total_cells_scanned": extraction.summary.total_cells_scanned,
            "total_occurrences": extraction.summary.total_occurrences,
            "unique_urls": extraction.summary.unique_urls,
            "rejected_cells": extraction.summary.rejected_cells,
        },
        "results": items,
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_csv_with_locations(enriched, out: Path) -> None:
    """One row per occurrence (so a URL in 5 cells produces 5 rows)."""
    fields = [
        "sheet", "cell", "original_url", "final_url", "classification",
        "http_status", "likely_reason", "error_detail",
        "response_time_ms", "method_used", "attempts", "checked_at_utc",
    ]
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for e in enriched:
            d = e.result.to_dict()
            for o in e.occurrences:
                row = {k: d.get(k, "") for k in fields}
                row["sheet"] = o.sheet
                row["cell"] = o.cell
                w.writerow(row)
            if not e.occurrences:
                row = {k: d.get(k, "") for k in fields}
                row["sheet"] = ""
                row["cell"] = ""
                w.writerow(row)


def _resolve_output(
    user_path: Optional[Path],
    user_format: Optional[str],
    *,
    excel_mode: bool,
) -> tuple[Optional[Path], Optional[str]]:
    """Decide the (path, format) for writing results.

    Rules:
    - If --output and --format are both set, honor both. The path's
      extension is left as the user typed it (we don't rewrite it).
    - If --output is set without --format, infer from the file extension
      (.xlsx -> xlsx, .csv -> csv, .json -> json). Unknown extensions
      default to json.
    - If --format is set without --output, generate a filename:
      url_issues_YYYY-MM-DD.xlsx for xlsx; results.{ext} otherwise.
    - If neither is set:
        * Excel input mode -> default to writing the Phase 3 xlsx report
          (url_issues_YYYY-MM-DD.xlsx in CWD), since that's the primary
          deliverable for end users.
        * Plain URL mode  -> no output file (engine summary is enough).
    """
    if user_path is None and user_format is None:
        if excel_mode:
            from .excel_output import default_output_filename
            return Path(default_output_filename()), "xlsx"
        return None, None

    fmt = user_format
    path = user_path

    if path is not None and fmt is None:
        ext = path.suffix.lower()
        if ext == ".xlsx":
            fmt = "xlsx"
        elif ext == ".csv":
            fmt = "csv"
        elif ext == ".json":
            fmt = "json"
        else:
            fmt = "json"  # safe default for unknown extensions

    if path is None and fmt is not None:
        if fmt == "xlsx":
            from .excel_output import default_output_filename
            path = Path(default_output_filename())
        else:
            path = Path(f"results.{fmt}")

    return path, fmt


def _print_summary(results: list[UrlCheckResult]) -> None:
    total = len(results)
    ok = sum(1 for r in results if r.classification == Classification.OK)
    broken = sum(1 for r in results if r.classification == Classification.BROKEN)
    blocked = sum(
        1 for r in results if r.classification == Classification.POSSIBLY_BLOCKED
    )
    print()
    print("=" * 50)
    print(f"  Total checked      : {total}")
    print(f"  OK                 : {ok}")
    print(f"  Broken             : {broken}")
    print(f"  Possibly blocked   : {blocked}")
    print("=" * 50)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # ---- Excel-only flow (with optional plain URLs alongside) ----
    if args.excel is not None:
        extraction = _run_excel_extraction(args)
        urls = list(extraction.unique_urls)

        text_urls = _gather_text_urls(args)
        seen = set(urls)
        for u in text_urls:
            if u not in seen:
                seen.add(u)
                urls.append(u)

        if args.detect_only:
            payload = {
                "selection": {
                    "sheet": extraction.selection.sheet,
                    "column": extraction.selection.column,
                    "column_letter": extraction.selection.column_letter,
                    "header": extraction.selection.header,
                },
                "summary": {
                    "total_cells_scanned": extraction.summary.total_cells_scanned,
                    "total_occurrences": extraction.summary.total_occurrences,
                    "unique_urls": extraction.summary.unique_urls,
                    "rejected_cells": extraction.summary.rejected_cells,
                },
                "urls": [
                    {
                        "url": u,
                        "locations": [o.location for o in extraction.occurrences_map[u]],
                    }
                    for u in extraction.unique_urls
                ],
            }
            text = json.dumps(payload, indent=2)
            if args.output:
                args.output.write_text(text, encoding="utf-8")
                print(f"Wrote detection preview to {args.output}")
            else:
                print(text)
            return 0

        if not urls:
            print("error: no checkable URLs found.", file=sys.stderr)
            return 2

        settings = _settings_from_args(args)
        progress_cb = None if args.quiet else _make_progress_printer(len(urls))
        if not args.quiet:
            print(f"Checking {len(urls)} unique URL(s)...", file=sys.stderr)

        check_urls_sync = _import_engine()
        results = check_urls_sync(urls, settings=settings, progress_cb=progress_cb)

        from .excel_input import enrich_results_with_occurrences
        enriched = enrich_results_with_occurrences(results, extraction.occurrences_map)

        _print_summary(results)

        out_path, out_format = _resolve_output(args.output, args.format, excel_mode=True)
        if out_path is not None:
            if out_format == "xlsx":
                from .excel_output import build_output_rows, write_excel_report
                broken_rows, blocked_rows = build_output_rows(enriched)
                written = write_excel_report(broken_rows, blocked_rows, out_path)
                print(f"Wrote Excel report to {written}")
                print(f"  Broken URLs       : {len(broken_rows)}")
                print(f"  Possibly blocked  : {len(blocked_rows)}")
            elif out_format == "json":
                _write_json_with_locations(enriched, extraction, out_path)
                print(f"Wrote results to {out_path}")
            elif out_format == "csv":
                _write_csv_with_locations(enriched, out_path)
                print(f"Wrote results to {out_path}")
        return 0

    # ---- Plain URL flow (Phase 1 behavior, unchanged) ----
    urls = _gather_text_urls(args)
    if not urls:
        parser.print_usage(sys.stderr)
        print("error: no URLs provided (pass positionally, --input, or --excel)",
              file=sys.stderr)
        return 2

    settings = _settings_from_args(args)
    progress_cb = None if args.quiet else _make_progress_printer(len(urls))
    if not args.quiet:
        print(f"Checking {len(urls)} URL(s) "
              f"(concurrency={settings.concurrency}, "
              f"timeout={settings.timeout}s, retries={settings.retries})...",
              file=sys.stderr)

    check_urls_sync = _import_engine()
    results = check_urls_sync(urls, settings=settings, progress_cb=progress_cb)
    _print_summary(results)

    out_path, out_format = _resolve_output(args.output, args.format, excel_mode=False)
    if out_path is not None:
        if out_format == "xlsx":
            # In plain-URL mode there are no cell locations — synthesize
            # empty-locations enriched items so the report can still be
            # produced (broken/blocked sheets just have a blank "Cell
            # Location(s)" column).
            from .excel_output import build_output_rows, write_excel_report

            class _PlainEnriched:
                __slots__ = ("result", "locations")
                def __init__(self, r): self.result = r; self.locations = []

            enriched = [_PlainEnriched(r) for r in results]
            broken_rows, blocked_rows = build_output_rows(enriched)
            written = write_excel_report(broken_rows, blocked_rows, out_path)
            print(f"Wrote Excel report to {written}")
            print(f"  Broken URLs       : {len(broken_rows)}")
            print(f"  Possibly blocked  : {len(blocked_rows)}")
        elif out_format == "json":
            _write_json_simple(results, out_path)
            print(f"Wrote results to {out_path}")
        elif out_format == "csv":
            _write_csv_simple(results, out_path)
            print(f"Wrote results to {out_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
