# Tests

Behavioral tests for the URL Health Checker. Run them all with:

```bash
python -m unittest discover -s tests -v
```

## File map

| File | What it covers |
|---|---|
| `test_url_normalize.py` | All public functions of `urlcheck.url_normalize`: stripping, bracket-balance preservation, scheme rejection, www-promotion, split logic, end-to-end extraction, structural URL validation. |
| `test_signatures.py` | Header, body, combined, and status-based bot-protection detection in `urlcheck.signatures` (Cloudflare, Akamai, PerimeterX, DataDome, generic CAPTCHA), plus false-positive guards for the tightened Akamai pattern. |
| `test_excel_output.py` | `urlcheck.excel_output` writer behavior: sheet names, column order, sort order, frozen panes, All-Clear path, golden round-trip against `fixtures/sample_report.xlsx`. |
| `test_excel_input_errors.py` | Typed exception classes in `urlcheck.excel_input` (`ExcelFileNotFound`, `InvalidExcelFile`, `SheetNotFound`, `HeaderNotFound`, `InvalidColumnReference`, `ColumnNotFound`): every raise site, exception attributes, backwards-compatibility, and `worker._friendly_excel_error` dispatch by class. |
| `test_integration.py` | End-to-end extract → enrich → write pipeline against a synthetic input workbook. Uses canned `UrlCheckResult` objects in place of the engine (no network). |
| `test_icon_root_lookup.py` | Marker-based project-root lookup in `urlcheck.gui.icon`: `_find_project_root` survives package-tree refactors; `_candidate_paths` correctly branches between frozen and dev modes. |
| `test_worker_logging.py` | GUI worker's exception logging: full traceback routed through `applog` (not stderr, so frozen builds keep the diagnostic); user-facing dialog message is traceback-free. Stubs PySide6 to run without Qt. |
| `test_worker_eta_warmup.py` | `_ProgressReporter` ETA warm-up suppression: prevents inflated headline ETA from a single slow first URL. Drives `time.monotonic` via `unittest.mock` for deterministic timing. |
| `test_cli_entry.py` | CLI entry-point wiring: `python -m urlcheck --help` (subprocess), `urlcheck.cli.main` in-process, `--detect-only` works without aiohttp, file-layout regression guards (`__main__.py` exists, `cli.py` is inside the package), lazy public API doesn't pull aiohttp. |
| `test_gui_package_layout.py` | Minimal structural smoke: GUI modules exist where expected; no `logging.py` shadowing stdlib. **No behavior assertions.** |

## Fixtures

`fixtures/sample_report.xlsx` — a reference output report. The
`GoldenAgainstSampleReport` class in `test_excel_output.py` builds matching
input rows and verifies the writer reproduces the fixture cell-for-cell.
If the report contract (column order, sheet names, sort behavior) ever
changes, regenerate this fixture.

## What was removed

The previous test files `test_phase4.py` and `test_phase6.py` were
AST-grep tests that asserted strings appeared in source code (e.g.
`self.assertIn('"Checking…"', src)`). They:

- passed when behavior was broken (they checked code shape, not behavior);
- failed during innocent refactors (e.g. moving a string to a constant);
- gave maintainers no signal about whether the app actually worked.

They have been replaced by the behavior-focused files above. A small
amount of structural-smoke value (checking module presence) has been
preserved in `test_gui_package_layout.py`.

## Test design notes

- Tests are **black-box**: they import the public functions and exercise
  them via inputs and outputs. They don't inspect source text.
- Tests for the engine itself (`urlcheck.engine`) are not included here
  because they would require either real network access or a non-trivial
  HTTP mock harness. The engine's individual pieces are exercised via
  `test_signatures.py`; full HTTP behavior is left to manual QA.
- The integration test stubs the engine layer with canned results, so it
  runs offline and is fully deterministic.
