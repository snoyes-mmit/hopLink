# URL Health Checker

A desktop tool (with optional CLI) that opens an Excel workbook, checks every URL inside it, and produces a focused Excel report listing only the URLs that didn't work — along with the exact cell each one came from.

Designed for non-technical reviewers: drag-and-drop input, friendly errors, no terminal required for the GUI. Built on `aiohttp`, `openpyxl`, and `PySide6`.

> **For non-technical users:** see [`USER_GUIDE.md`](USER_GUIDE.md) for a plain-English walkthrough of the desktop app.

---

## Features

- **Drag-and-drop Excel input** — `.xlsx` files, with sheet and URL-column auto-detection.
- **Async URL checking** — HEAD-first with GET fallback, configurable concurrency, per-domain throttling, retries with exponential backoff and jitter.
- **Three-way classification** — `OK` / `BROKEN` / `POSSIBLY_BLOCKED`, with bot-protection detection for Cloudflare, Akamai, PerimeterX, DataDome, and generic CAPTCHA challenges.
- **Cell-location tracking** — every URL is reported with the list of cells where it appeared, so reviewers can jump straight to the source.
- **Two-sheet report** — "Broken URLs" and "Possibly Blocked" only; clean URLs are omitted to reduce noise. Sorted by domain so blocking patterns cluster visually.
- **All-Clear path** — if every URL works, the report is a single-sheet record-keeping workbook.
- **Cancellation** — runs can be cancelled mid-flight without freezing the UI.
- **Persistent settings** — last-used file, sheet, column, and tuning values are remembered across sessions.
- **Rotating file log** — diagnostic info lands in `%APPDATA%\urlcheck\logs\` (Windows) / `~/Library/Logs/urlcheck/` (macOS) / `~/.local/share/urlcheck/logs/` (Linux). Useful for support cases.

---

## Tech Stack

| Layer            | Technology                                                   |
|------------------|--------------------------------------------------------------|
| Async HTTP       | `aiohttp` (TaskGroup, semaphore-based concurrency)           |
| Excel I/O        | `openpyxl` (read-only loading, hyperlink-aware extraction)   |
| Desktop GUI      | `PySide6` (Qt 6 for Python)                                  |
| Packaging        | `PyInstaller`                                                |
| Test framework   | stdlib `unittest`                                            |
| Python           | **3.11+ required** (uses `asyncio.TaskGroup`)                |

---

## Folder Structure

```
url-health-checker/
├── app.py                    GUI entry point — `python app.py`
├── urlcheck.spec             PyInstaller spec — canonical build config
├── requirements.txt          Pinned lower-bound dependencies
├── build.bat / build.sh      Platform wrappers around build_tools/build.py
├── README.md                 This file
├── USER_GUIDE.md             Non-technical user guide
│
├── urlcheck/                 Library code
│   ├── __init__.py           Public API (lazy engine re-export via PEP 562)
│   ├── __main__.py           Entry point for `python -m urlcheck`
│   ├── cli.py                Command-line interface (argparse)
│   ├── engine.py             Async URL-checking engine
│   ├── models.py             Settings, UrlCheckResult, Classification
│   ├── signatures.py         Bot-protection detection (headers + body + status)
│   ├── url_normalize.py      URL parsing / extraction / stripping
│   ├── excel_input.py        Workbook reading, column auto-detection, extraction
│   ├── excel_output.py       Two-sheet "issues" report writer
│   └── gui/                  PySide6 desktop wrapper
│       ├── __init__.py
│       ├── main_window.py    QMainWindow + UI flow
│       ├── worker.py         QThread background worker + cancellation
│       ├── signals.py        WorkerSignals (QObject with Signal members)
│       ├── widgets.py        DropZone, CollapsiblePanel, format_eta
│       ├── settings.py       QSettings persistence wrapper
│       ├── applog.py         File logger with rotation
│       └── icon.py           Marker-based app-icon resolver (PyInstaller-aware)
│
├── build_tools/              Packaging helpers
│   └── build.py              PyInstaller driver (--mode onedir|onefile, --debug, --clean)
│
└── tests/                    Behavioral test suite (244 tests, ~0.6s, fully offline)
    ├── README.md             Per-file test map and design notes
    ├── fixtures/
    │   └── sample_report.xlsx
    ├── test_url_normalize.py
    ├── test_signatures.py
    ├── test_excel_output.py
    ├── test_excel_input_errors.py
    ├── test_integration.py
    ├── test_icon_root_lookup.py
    ├── test_worker_logging.py
    ├── test_worker_eta_warmup.py
    ├── test_cli_entry.py
    └── test_gui_package_layout.py
```

---

## Requirements

- **Python 3.11 or newer** (the engine relies on `asyncio.TaskGroup`).
- For the GUI: a working PySide6/Qt 6 installation. PySide6 ships its own Qt so this is usually transparent.
- For builds: `pyinstaller` (already in `requirements.txt`).

OS-wise, the code is portable across Windows, macOS, and Linux. The build flow targets Windows (`.exe`) and macOS (`.app`) primarily; Linux is supported as a side effect.

---

## Installation

```bash
# 1. Clone or unzip the project
cd url-health-checker

# 2. (Recommended) Create and activate a virtual environment
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt
```

> If you only need to run the test suite or use the Excel input layer without HTTP, you can skip `aiohttp` and `PySide6`. The Excel layer is independent of the engine.

---

## Configuration

The application uses **no environment files (`.env`) and no secrets**. There is nothing to configure before running it. All tunables (concurrency, timeout, retries, per-domain delay, header row, auto-https) are exposed in the GUI's *Advanced* panel and persisted across sessions via Qt's platform-standard storage (`QSettings`):

| Platform | Storage                                                  |
|----------|----------------------------------------------------------|
| Windows  | Registry under `HKEY_CURRENT_USER\Software\urlcheck`     |
| macOS    | `~/Library/Preferences/com.urlcheck.URL Health Checker.plist` |
| Linux    | `~/.config/urlcheck/URL Health Checker.conf`             |

A rotating diagnostic log is written to (see *Troubleshooting* below for what's in it):

| Platform | Log path                                                  |
|----------|-----------------------------------------------------------|
| Windows  | `%APPDATA%\urlcheck\logs\urlchecker.log`                  |
| macOS    | `~/Library/Logs/urlcheck/urlchecker.log`                  |
| Linux    | `~/.local/share/urlcheck/logs/urlchecker.log`             |

---

## Running the App (Desktop GUI)

```bash
python app.py
```

This is the main entry point. The flow is:

1. **Choose an Excel file** — drag-drop onto the drop zone or click to browse.
2. **Choose sheet** — auto-populated; auto-detection picks the best sheet. The column dropdown defaults to **"Auto-detect — scan every column"**, so by default HopLink finds URLs anywhere on the sheet. Pick a single column only if you want to narrow the scan.
3. **(Optional) Tune Advanced settings** — collapsed by default.
4. **Click "Check URLs"** — runs in a background thread. The UI stays responsive.
5. **Cancel** — visible only during a run; clean unwind with no force-kill.
6. **Save Results** — opens a *Save As* dialog and writes the two-sheet report.

If every URL returns HTTP 200, a single-sheet "All Clear" workbook is written so reviewers have a record that the check ran.

---

## Running the App (CLI)

The CLI is invoked via `python -m urlcheck`. It handles both plain-text URL lists and Excel input.

```bash
# Plain text URLs
python -m urlcheck https://example.com https://example.org
python -m urlcheck --input urls.txt --concurrency 50 --timeout 15

# Excel input → two-sheet issue report
python -m urlcheck --excel links.xlsx
python -m urlcheck --excel links.xlsx --sheet Links --column URL
python -m urlcheck --excel links.xlsx --output report.xlsx

# Preview what would be checked, no HTTP (no aiohttp required for this path)
python -m urlcheck --excel links.xlsx --detect-only
```

See `python -m urlcheck --help` for the full flag list. The CLI mirrors the GUI's tuning knobs (`--concurrency`, `--timeout`, `--retries`, `--per-domain-delay`, `--header-row`, `--auto-https`).

---

## Testing

The full test suite is 244 behavioral tests, runs in under a second, with no network access required:

```bash
python -m unittest discover -s tests -v
```

What's covered (see `tests/README.md` for the per-file map):

- **URL normalization** — stripping, bracket-balance preservation, scheme rejection, structural validation.
- **Bot-protection signatures** — header / body / combined detection for each vendor, plus false-positive guards (e.g. Akamai pattern doesn't fire on academic prose).
- **Excel output writer** — sheet layout, column order, sort order, frozen panes, All-Clear path. Includes a **golden round-trip** that rebuilds `tests/fixtures/sample_report.xlsx` from scratch and asserts cell-for-cell equality.
- **Excel input errors** — typed exception classes (`ExcelFileNotFound`, `SheetNotFound`, `HeaderNotFound`, etc.) with backwards-compatibility (still catchable as `ValueError` / `FileNotFoundError`).
- **End-to-end integration** — synthetic input workbook through extract → enrich → write, with the engine layer stubbed by canned `UrlCheckResult` objects.
- **GUI worker behavior** — exception logging via `applog` (not stderr, so frozen builds keep the diagnostic), ETA warm-up suppression (prevents the inflated "5940-second ETA from one slow URL" surprise), and the GUI package layout.
- **CLI entry point** — `python -m urlcheck --help` exits 0 (verified via subprocess), `urlcheck.cli.main` is callable in-process, `--detect-only` works without aiohttp, and the lazy public API (`from urlcheck import Classification, …`) doesn't pull aiohttp at import time.

The test suite stubs PySide6 internally where needed, so it can be run on a CI box without Qt installed.

---

## Linting / Formatting

No linter or formatter is currently wired into the repo. Recommended tools and one-liners:

```bash
# Quick style check (drop-in, no config)
pip install ruff
ruff check .
ruff format .

# Type-checking (best-effort; some PySide6 type stubs are imperfect)
pip install mypy
mypy urlcheck
```

---

## Build / Packaging (Standalone Executable)

For end users who don't have Python, the app can be packaged into a Windows `.exe` or macOS `.app` via PyInstaller.

```bash
# Recommended: onedir build (faster startup, easier to debug)
python build_tools/build.py

# Single-file build (slower startup, but ships as one .exe)
python build_tools/build.py --mode onefile

# Debug build (keeps the console window open alongside the GUI)
python build_tools/build.py --debug

# Wipe build/ and dist/ before rebuilding
python build_tools/build.py --clean
```

Platform shortcuts:

```bash
# Windows
build.bat --mode onedir

# macOS / Linux
./build.sh --mode onedir
```

### Build outputs

| Platform | Mode      | Path                                                  |
|----------|-----------|-------------------------------------------------------|
| Windows  | onedir    | `dist/urlcheck/urlcheck.exe`  (+ DLLs in same folder) |
| Windows  | onefile   | `dist/urlcheck.exe`                                   |
| macOS    | onedir    | `dist/URL Health Checker.app`                         |
| macOS    | onefile   | `dist/URL Health Checker.app`                         |
| Linux    | onedir    | `dist/urlcheck/urlcheck`                              |
| Linux    | onefile   | `dist/urlcheck`                                       |

### Optional: app icons

Drop `icon.ico` (Windows) or `icon.icns` (macOS) into `build_tools/assets/` and they'll be picked up automatically. The build does not fail if the directory or files are missing.

### Code-signing notes

Unsigned PyInstaller `.exe` files trigger Windows SmartScreen warnings on first run. Unsigned macOS `.app` bundles trigger Gatekeeper. For wider distribution, sign the artifacts; for internal use, see *Troubleshooting* below.

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'aiohttp'" (or `PySide6`, `openpyxl`) on launch

`pip install -r requirements.txt` wasn't run, or it ran in a different Python environment than the one launching the app. With a virtual environment, make sure it's activated.

### The GUI starts but every URL shows as "broken"

You may be behind a corporate proxy or VPN that blocks outbound connections from non-browser processes. The engine respects `HTTP_PROXY` / `HTTPS_PROXY` environment variables (via `aiohttp`'s `trust_env=True`); set those if your network requires a proxy.

### The GUI starts but "Possibly Blocked" results dominate

Some domains (Cloudflare, Akamai, etc.) block all non-browser traffic. The tool reports faithfully what the server said. Spot-check one or two in a browser; if they work there, the site simply doesn't trust automated requests.

### Build succeeds but the frozen binary crashes on launch

Build with `--debug` and read the console output. The most common cause is a missing hidden import; `urlcheck.spec` already collects submodules for `aiohttp`, `openpyxl`, and friends, but if a new dependency is added you may need to extend the spec.

### Windows SmartScreen blocks the `.exe` from running

Click *More info* → *Run anyway*. For internal distribution, ask IT to allowlist the binary or buy a code-signing certificate. See the *Code-signing notes* section above.

### macOS: "App is damaged and can't be opened"

```bash
xattr -dr com.apple.quarantine "dist/URL Health Checker.app"
```

This strips the quarantine attribute Gatekeeper adds to unsigned bundles. For wider distribution, sign and notarize via an Apple Developer ID.

### Where are the logs?

Per the *Configuration* section above:

- Windows: `%APPDATA%\urlcheck\logs\urlchecker.log`
- macOS: `~/Library/Logs/urlcheck/urlchecker.log`
- Linux: `~/.local/share/urlcheck/logs/urlchecker.log`

The log rotates at 1 MB and keeps 3 backups. Attach the most recent file when reporting an issue.

---

## Known Issues / Risks

These are limitations and risks identified during the production-readiness review. The first item requires a code change to address; the rest are by-design limitations of the approach.

1. **`build_tools/smoke_test.py` is referenced but missing.** Earlier documentation mentioned a post-build smoke test; the file doesn't exist. The build script itself doesn't reference it, so this is purely a documentation-drift issue.

2. **Soft-404s are out of scope by design.** A site that returns HTTP 200 with a "page not found" body is classified `OK`.

3. **JavaScript-only sites.** No headless browser is used; the tool checks the underlying URL, not the rendered page.

4. **Login-protected URLs** show as broken (`401 Unauthorized` or similar). There's no credential-passing facility.

5. **Hostname tolerance is deliberately lenient.** URLs with unusual hosts (double-dot, leading-hyphen) pass the validator. The engine will fail them at the DNS stage and produce a clearly-labeled BROKEN row, which is preferred over silently dropping data. Pinned by `test_accepts_typo_hosts_by_design`.

---

## License / Attribution

No license file is shipped with the project. If you intend to distribute this software, add a `LICENSE` file at the project root before doing so.

Third-party dependencies (`aiohttp`, `openpyxl`, `PySide6`, `certifi`, `pyinstaller`) carry their own licenses; consult each package's homepage for terms.

---

## Project History

This repository was developed in phases, each documented in the original README:

| Phase | Scope                                                          |
|-------|----------------------------------------------------------------|
| 1     | Async engine + plain-URL CLI                                   |
| 2     | Excel input layer with cell-location tracking                  |
| 3     | Two-sheet "issues" Excel report writer                         |
| 4     | PySide6 desktop GUI                                            |
| 5     | PyInstaller packaging (`build.py`, `urlcheck.spec`)            |
| 6     | UX polish (settings persistence, friendly errors, drag-drop states, logging) |
| 7     | Production-readiness review and behavioral test suite — replaced the original AST-grep tests with 230 behavioral assertions covering URL normalization, signatures, Excel I/O, end-to-end pipeline, worker logging, ETA warm-up, and typed Excel exceptions. |
| 8     | CLI entry-point fix (this snapshot) — moved `cli.py` into the `urlcheck/` package, added `__main__.py`, and populated `__init__.py` with a lazy public API. Added 14 entry-point tests covering subprocess invocation, in-process `main()`, file-layout regression guards, and the laziness of the public API. |
