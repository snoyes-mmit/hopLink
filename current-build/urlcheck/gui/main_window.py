"""Main window for the URL-checker GUI.

Layout (top to bottom):
    1. File input section (drop zone + browse button)
    2. Sheet + column selectors (auto-populated on file load)
    3. Collapsible "Advanced settings" panel
    4. Big "Check URLs" button
    5. Progress section (bar + counters + ETA)
    6. Cancel / Save Results buttons

Threading:
    All heavy work runs in a Worker QThread. The window holds a reference
    to the active worker, connects to its signals, and never accesses
    its internal state directly. Cancel is signal-out; everything else
    is signal-in.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QUrl, Slot
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..models import Settings
from .applog import get_logger
from .icon import load_app_icon
from .settings import (
    AppSettings,
    SAFE_DEFAULT_CONCURRENCY,
    SAFE_DEFAULT_PER_DOMAIN_DELAY,
    SAFE_DEFAULT_RETRIES,
    SAFE_DEFAULT_TIMEOUT,
)
from .widgets import CollapsiblePanel, DropZone, format_eta
from .worker import AUTO_DETECT_ALL_COLUMNS, CheckJob, Worker


APP_TITLE = "URL Health Checker"


class MainWindow(QMainWindow):
    """Top-level application window.

    The state machine is small enough to track with a single _state field:
        "idle"      → no run in progress; can pick a file / start
        "running"   → worker thread is active; only Cancel is enabled
        "completed" → results in memory; can save or start a new run
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(720, 640)

        # Application icon (window + taskbar/dock).
        self.setWindowIcon(load_app_icon())

        # Persisted preferences + internal logger.
        self._app_settings = AppSettings()
        self._log = get_logger()
        self._log.info("Application started")

        # Track the most recently-saved report so we can offer a
        # "show in folder" action.
        self._last_saved_report: Optional[Path] = None

        # ---- State ----
        self._excel_path: Optional[Path] = None
        self._sheets: list[str] = []
        self._column_candidates: list = []  # list of ColumnCandidate
        self._worker: Optional[Worker] = None
        self._results: Optional[list] = None  # last completed run's enriched results
        self._state: str = "idle"

        # ---- UI ----
        self._build_ui()
        self._wire_signals()
        self._restore_settings()
        self._set_state("idle")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        # ----- Friendly intro -----
        intro = QLabel(
            "Check thousands of URLs in your spreadsheet for broken links. "
            "Drop a file below to begin."
        )
        intro.setStyleSheet("color: #555; padding: 0 0 4px 0;")
        intro.setWordWrap(True)
        outer.addWidget(intro)

        # ----- File input -----
        outer.addWidget(self._build_section_label("1. Choose Excel file"))
        self._drop_zone = DropZone()
        outer.addWidget(self._drop_zone)

        # ----- Sheet & column selectors -----
        # The column picker is optional — by default we scan every
        # column on the chosen sheet. The dropdown still lets the user
        # narrow the scan to one column if they want to.
        outer.addWidget(self._build_section_label("2. Choose sheet (column is optional)"))
        sheet_col_row = QHBoxLayout()
        sheet_col_row.setSpacing(12)

        sheet_label = QLabel("Sheet:")
        self._sheet_combo = QComboBox()
        self._sheet_combo.setMinimumWidth(180)
        self._sheet_combo.setEnabled(False)

        column_label = QLabel("Column:")
        self._column_combo = QComboBox()
        self._column_combo.setMinimumWidth(260)
        self._column_combo.setEnabled(False)
        self._column_combo.setToolTip(
            "By default HopLink scans every column on the sheet for URLs. "
            "Use this dropdown only if you want to restrict the scan to a "
            "single column."
        )

        sheet_col_row.addWidget(sheet_label)
        sheet_col_row.addWidget(self._sheet_combo)
        sheet_col_row.addSpacing(20)
        sheet_col_row.addWidget(column_label)
        sheet_col_row.addWidget(self._column_combo)
        sheet_col_row.addStretch(1)
        outer.addLayout(sheet_col_row)

        # ----- Advanced settings (collapsible) -----
        self._adv_panel = CollapsiblePanel("Advanced settings (most users can ignore these)")
        adv_form = QFormLayout()
        adv_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._concurrency_spin = QSpinBox()
        self._concurrency_spin.setRange(1, 200)
        self._concurrency_spin.setValue(SAFE_DEFAULT_CONCURRENCY)
        self._concurrency_spin.setToolTip(
            "Number of URLs checked at once. Higher = faster but uses more "
            "network. Recommended: 5–10 for most networks."
        )
        adv_form.addRow("Concurrency:", self._concurrency_spin)

        self._timeout_spin = QDoubleSpinBox()
        self._timeout_spin.setRange(1.0, 300.0)
        self._timeout_spin.setSingleStep(1.0)
        self._timeout_spin.setSuffix(" s")
        self._timeout_spin.setValue(SAFE_DEFAULT_TIMEOUT)
        self._timeout_spin.setToolTip(
            "Seconds to wait for each URL before giving up."
        )
        adv_form.addRow("Timeout:", self._timeout_spin)

        self._retries_spin = QSpinBox()
        self._retries_spin.setRange(0, 10)
        self._retries_spin.setValue(SAFE_DEFAULT_RETRIES)
        self._retries_spin.setToolTip(
            "How many extra times to try a URL if it fails or times out."
        )
        adv_form.addRow("Retries:", self._retries_spin)

        self._delay_spin = QDoubleSpinBox()
        self._delay_spin.setRange(0.0, 10.0)
        self._delay_spin.setSingleStep(0.05)
        self._delay_spin.setDecimals(2)
        self._delay_spin.setSuffix(" s")
        self._delay_spin.setValue(SAFE_DEFAULT_PER_DOMAIN_DELAY)
        self._delay_spin.setToolTip(
            "Minimum gap between requests to the same website. Higher = "
            "politer to small servers, less likely to be rate-limited."
        )
        adv_form.addRow("Per-domain delay:", self._delay_spin)

        self._header_row_spin = QSpinBox()
        self._header_row_spin.setRange(0, 100)
        self._header_row_spin.setValue(1)
        self._header_row_spin.setToolTip(
            "Row containing the column headers. Use 0 if your file has no "
            "header row."
        )
        adv_form.addRow("Header row:", self._header_row_spin)

        self._auto_https_check = QCheckBox("Treat bare domains as https:// URLs")
        self._auto_https_check.setToolTip(
            "If on, cells like 'example.com' are checked as 'https://example.com'."
        )
        adv_form.addRow("", self._auto_https_check)

        self._adv_panel.add_layout(adv_form)
        outer.addWidget(self._adv_panel)

        # ----- Action button -----
        self._check_btn = QPushButton("Check URLs")
        self._check_btn.setMinimumHeight(40)
        self._check_btn.setStyleSheet(
            "QPushButton { font-size: 14px; font-weight: 600; }"
        )
        self._check_btn.setToolTip(
            "Visit every URL in the selected column to verify it's reachable."
        )
        outer.addWidget(self._check_btn)

        # ----- Progress section -----
        outer.addWidget(self._build_section_label("Progress"))

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)  # indeterminate until total is known
        self._progress_bar.setTextVisible(True)
        outer.addWidget(self._progress_bar)

        counter_row = QHBoxLayout()
        counter_row.setSpacing(20)
        self._lbl_checked = QLabel("Checked: 0 / 0")
        self._lbl_ok = QLabel("OK: 0")
        self._lbl_broken = QLabel("Broken: 0")
        self._lbl_blocked = QLabel("Possibly blocked: 0")
        self._lbl_eta = QLabel("ETA: —")
        for lbl in (self._lbl_checked, self._lbl_ok, self._lbl_broken,
                    self._lbl_blocked, self._lbl_eta):
            lbl.setStyleSheet("QLabel { padding: 2px 6px; }")
        counter_row.addWidget(self._lbl_checked)
        counter_row.addWidget(self._lbl_ok)
        counter_row.addWidget(self._lbl_broken)
        counter_row.addWidget(self._lbl_blocked)
        counter_row.addStretch(1)
        counter_row.addWidget(self._lbl_eta)
        outer.addLayout(counter_row)

        # Divider before action buttons.
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        outer.addWidget(line)

        # ----- Cancel + Save Results -----
        action_row = QHBoxLayout()
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setVisible(False)
        self._cancel_btn.setToolTip("Stop the run. In-flight requests finish naturally.")
        action_row.addWidget(self._cancel_btn)

        action_row.addStretch(1)

        self._show_btn = QPushButton("Show in folder")
        self._show_btn.setEnabled(False)
        self._show_btn.setToolTip(
            "Open the folder containing the saved report."
        )
        action_row.addWidget(self._show_btn)

        self._save_btn = QPushButton("Save Results…")
        self._save_btn.setEnabled(False)
        self._save_btn.setMinimumHeight(34)
        self._save_btn.setStyleSheet(
            "QPushButton { font-weight: 600; padding: 4px 16px; }"
        )
        self._save_btn.setToolTip(
            "Write the issues report to an Excel file you can share with colleagues."
        )
        action_row.addWidget(self._save_btn)
        outer.addLayout(action_row)

        outer.addStretch(1)

        # ----- Status bar -----
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(
            "Ready. Drop an Excel file above to begin."
        )

        # ----- Menu (just an Exit shortcut for keyboard users) -----
        file_menu = self.menuBar().addMenu("&File")
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

    @staticmethod
    def _build_section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("QLabel { font-weight: 600; }")
        return lbl

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _wire_signals(self) -> None:
        self._drop_zone.file_dropped.connect(self._on_file_chosen)
        self._drop_zone.browse_requested.connect(self._on_browse_clicked)
        self._sheet_combo.currentIndexChanged.connect(self._on_sheet_changed)
        self._check_btn.clicked.connect(self._on_check_clicked)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        self._save_btn.clicked.connect(self._on_save_clicked)
        self._show_btn.clicked.connect(self._on_show_in_folder_clicked)

    # ------------------------------------------------------------------
    # File selection handlers
    # ------------------------------------------------------------------

    @Slot()
    def _on_browse_clicked(self) -> None:
        start_dir = str(self._excel_path.parent) if self._excel_path else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Excel file", start_dir, "Excel files (*.xlsx)"
        )
        if path:
            self._on_file_chosen(path)

    @Slot(str)
    def _on_file_chosen(self, path: str, restoring: bool = False) -> None:
        p = Path(path)
        if not p.exists():
            self._show_error(
                "File not found",
                f"This file no longer exists:\n{path}\n\n"
                "It may have been moved or deleted. Please choose another file.",
            )
            return
        if p.suffix.lower() != ".xlsx":
            self._show_error(
                "Unsupported file type",
                "Only .xlsx files are supported. Older .xls files and other "
                "spreadsheet formats won't work — open the file in Excel "
                "and use 'Save As' to save it as .xlsx, then try again.",
            )
            return
        # Try opening it and pulling sheets/columns. This is fast even for
        # large workbooks because openpyxl streams the structure.
        try:
            from ..excel_input import (
                open_workbook, list_sheets,
            )
            wb = open_workbook(p)
            self._sheets = list_sheets(wb)
            if not self._sheets:
                self._show_error(
                    "Empty workbook",
                    "This Excel file has no sheets. Please choose a different file.",
                )
                return
            # Hold onto it transiently to populate column candidates without
            # re-opening. Will be closed at the end of this method.
            self._wb_handle = wb
        except PermissionError:
            self._show_error(
                "File is in use",
                "This file appears to be open in another program (likely Excel). "
                "Please close it there and try again.",
            )
            return
        except Exception as e:  # noqa: BLE001
            self._log.exception("Failed to open workbook %s", p)
            self._show_error(
                "Could not open file",
                f"Couldn't read this Excel file.\n\n"
                f"Details: {e}\n\n"
                "If the file is open in Excel, close it there and try again.",
            )
            return

        self._excel_path = p
        self._drop_zone.set_file(str(p))
        self._app_settings.set_last_file(p)
        self._log.info("Loaded workbook: %s", p)

        # Populate sheet combo. Block signals while we mutate to avoid
        # triggering _on_sheet_changed for each addItem call.
        self._sheet_combo.blockSignals(True)
        self._sheet_combo.clear()
        self._sheet_combo.addItems(self._sheets)
        self._sheet_combo.blockSignals(False)
        self._sheet_combo.setEnabled(True)

        # When restoring, prefer the user's previously-used sheet.
        last_sheet = self._app_settings.last_sheet() if restoring else ""
        chosen_sheet: Optional[str] = None
        if last_sheet and last_sheet in self._sheets:
            self._sheet_combo.setCurrentText(last_sheet)
            chosen_sheet = last_sheet
        else:
            # Auto-pick the sheet that looks most URL-bearing. We still
            # auto-select the SHEET because URL-bearing data is usually
            # confined to one tab, but we deliberately leave the column
            # dropdown on its default "Auto-detect — scan every column"
            # entry: with whole-sheet scanning available, there's no
            # reason to force the user (or ourselves) to single out a
            # column on a fresh file load.
            try:
                from ..excel_input import auto_pick_sheet_and_column
                best = auto_pick_sheet_and_column(
                    self._wb_handle,
                    scan_rows=50,
                    header_row=self._header_row_or_none(),
                )
            except Exception:
                best = None

            if best is not None and best.sheet in self._sheets:
                self._sheet_combo.setCurrentText(best.sheet)
                chosen_sheet = best.sheet
            else:
                self._sheet_combo.setCurrentIndex(0)

        # IMPORTANT: always populate the column combo explicitly.
        # `setCurrentText`/`setCurrentIndex` only fire `currentIndexChanged`
        # when the index actually changes — but after `addItems` Qt
        # auto-selects index 0, so re-selecting the same sheet (the common
        # case for a one-tab workbook) is a no-op and `_on_sheet_changed`
        # never runs, leaving the column combo empty and disabled.
        # Calling it directly here guarantees the column combo is
        # populated with the Auto-detect entry plus candidates.
        self._on_sheet_changed(self._sheet_combo.currentIndex())

        # When restoring, also try to re-select the user's previous column.
        if restoring:
            last_col = self._app_settings.last_column()
            if last_col > 0:
                self._select_column(last_col)

        self.statusBar().showMessage(f"Loaded {p.name}.")

    def _header_row_or_none(self) -> Optional[int]:
        v = self._header_row_spin.value()
        return v if v >= 1 else None

    @Slot(int)
    def _on_sheet_changed(self, _index: int) -> None:
        if not self._excel_path:
            return
        sheet_name = self._sheet_combo.currentText()
        if not sheet_name:
            return
        try:
            from ..excel_input import open_workbook, detect_url_columns
            # Re-open: cheap, and avoids holding workbook handles open while
            # the user pokes around.
            wb = open_workbook(self._excel_path)
            self._column_candidates = detect_url_columns(
                wb,
                sheet_name,
                scan_rows=50,
                header_row=self._header_row_or_none(),
            )
        except Exception as e:  # noqa: BLE001
            self._show_error("Could not read sheet", str(e))
            self._column_candidates = []

        # Populate column combo. First entry is always the auto-detect
        # option, which tells the worker to scan every column on the
        # sheet via `extract_urls_from_sheet`. The remaining entries are
        # the per-column candidates plus a fallback list of manual
        # column letters in case the heuristic misses one.
        self._column_combo.blockSignals(True)
        self._column_combo.clear()

        self._column_combo.addItem(
            "Auto-detect — scan every column",
            userData={"column_ref": AUTO_DETECT_ALL_COLUMNS},
        )

        for c in self._column_candidates:
            label = self._format_column_label(c)
            self._column_combo.addItem(
                label, userData={"column_ref": str(c.column), "column": c.column}
            )
        # Always offer manual-letter picks too, in case the heuristic
        # misses a column the user knows about.
        from openpyxl.utils import get_column_letter
        for col_idx in range(1, 27):  # A..Z is plenty for the GUI; users
                                       # with bigger files use the CLI.
            letter = get_column_letter(col_idx)
            if not any(c.column == col_idx for c in self._column_candidates):
                self._column_combo.addItem(
                    f"Column {letter} (manual)",
                    userData={"column_ref": str(col_idx), "column": col_idx},
                )
        self._column_combo.blockSignals(False)
        self._column_combo.setEnabled(self._column_combo.count() > 0)
        # Default to auto-detect — it's the first entry, but make it
        # explicit so the index is stable across re-population.
        self._column_combo.setCurrentIndex(0)

    @staticmethod
    def _format_column_label(c) -> str:
        """Pretty label for a ColumnCandidate."""
        header = f" — {c.header}" if c.header else ""
        return f"Column {c.column_letter}{header}  (URL match {c.score:.0%})"

    def _select_column(self, column_index: int) -> None:
        """Programmatically pick the combo entry whose userData matches."""
        for i in range(self._column_combo.count()):
            data = self._column_combo.itemData(i)
            if data and data.get("column") == column_index:
                self._column_combo.setCurrentIndex(i)
                return

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------

    @Slot()
    def _on_check_clicked(self) -> None:
        if self._state == "running":
            return
        # ---- Validate inputs ----
        if not self._excel_path:
            self._show_error(
                "No file selected",
                "Please drop or browse to an .xlsx file first.",
            )
            return
        if not self._sheet_combo.currentText():
            self._show_error(
                "No sheet selected",
                "Please pick a sheet from the dropdown.",
            )
            return
        col_data = self._column_combo.currentData()
        if not col_data or "column_ref" not in col_data:
            self._show_error(
                "No column selected",
                "Please pick a URL column from the dropdown, or leave it "
                "on \"Auto-detect — scan every column\".",
            )
            return

        # Persist settings now (so they survive even if the run is cancelled).
        self._save_settings()

        # ---- Build the job ----
        settings = replace(
            Settings(),
            concurrency=self._concurrency_spin.value(),
            timeout=self._timeout_spin.value(),
            retries=self._retries_spin.value(),
            per_domain_delay=self._delay_spin.value(),
        )
        job = CheckJob(
            excel_path=self._excel_path,
            sheet=self._sheet_combo.currentText(),
            # Either the AUTO_DETECT_ALL_COLUMNS sentinel or a numeric
            # column index in string form. The worker uses the sentinel
            # to switch to whole-sheet extraction; everything else flows
            # through the existing column-resolution path.
            column_ref=col_data["column_ref"],
            header_row=self._header_row_or_none(),
            settings=settings,
            auto_https=self._auto_https_check.isChecked(),
        )
        self._log.info(
            "Starting run: file=%s sheet=%s column=%s concurrency=%d",
            self._excel_path.name, job.sheet, job.column_ref, settings.concurrency,
        )

        # ---- Reset progress UI ----
        self._reset_progress_ui()

        # ---- Spawn the worker ----
        self._worker = Worker(job, parent=self)
        self._worker.signals.extraction_done.connect(self._on_extraction_done)
        self._worker.signals.progress_update.connect(self._on_progress_update)
        self._worker.signals.finished.connect(self._on_worker_finished)
        self._worker.signals.error.connect(self._on_worker_error)
        self._worker.signals.canceled.connect(self._on_worker_canceled)
        self._worker.finished.connect(self._on_thread_finished)

        self._set_state("running")
        self.statusBar().showMessage("Reading Excel file…")
        self._worker.start()

    @Slot()
    def _on_cancel_clicked(self) -> None:
        if self._worker is None or self._state != "running":
            return
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setText("Cancelling…")
        self.statusBar().showMessage("Cancelling — finishing in-flight requests…")
        self._worker.request_cancel()

    @Slot()
    def _on_save_clicked(self) -> None:
        if not self._results:
            return
        default_name = f"url_issues_{date.today().isoformat()}.xlsx"
        # Use the last-save dir if we have one; else next to the input file;
        # else the user's home dir as a last resort.
        last_save_dir = self._app_settings.last_save_dir()
        start_dir: Optional[Path] = None
        if last_save_dir is not None:
            start_dir = last_save_dir
        elif self._excel_path is not None:
            start_dir = self._excel_path.parent
        suggested = str((start_dir / default_name) if start_dir else Path(default_name))

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save report as",
            suggested,
            "Excel files (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            from ..excel_output import build_output_rows, write_excel_report
            broken, blocked = build_output_rows(self._results)
            written = write_excel_report(broken, blocked, path)
        except PermissionError:
            self._show_error(
                "Cannot save here",
                "The file may be open in Excel, or you don't have permission "
                "to write to this folder.\n\n"
                "Close it in Excel (or pick a different folder) and try again.",
            )
            return
        except Exception as e:  # noqa: BLE001
            self._log.exception("Failed to save report to %s", path)
            self._show_error(
                "Could not save report",
                f"Saving the report failed.\n\nDetails: {e}\n\n"
                "Try saving to a different folder, or restart the app and try again.",
            )
            return

        # Remember the directory for next time, and the file for the
        # "Show in folder" button.
        self._last_saved_report = written
        self._app_settings.set_last_save_dir(written.parent)
        self._show_btn.setEnabled(True)
        self._log.info(
            "Saved report: %s (broken=%d, blocked=%d)",
            written, len(broken), len(blocked),
        )

        QMessageBox.information(
            self,
            "Report saved",
            f"\u2705 Saved to:\n{written}\n\n"
            f"\u2022 Broken URLs:       {len(broken):,}\n"
            f"\u2022 Possibly blocked:  {len(blocked):,}\n\n"
            f"Click \u201cShow in folder\u201d to open the location.",
        )
        self.statusBar().showMessage(
            f"Saved {written.name}. Click 'Show in folder' to open it."
        )

    # ------------------------------------------------------------------
    # Worker signal handlers (run on the GUI thread)
    # ------------------------------------------------------------------

    @Slot(dict)
    def _on_extraction_done(self, payload: dict) -> None:
        unique = payload.get("unique_urls", 0)
        sheet = payload.get("sheet", "")
        col = payload.get("column_letter", "")
        # `column_letter == "*"` is the sentinel from `ExcelSelection`
        # meaning "whole-sheet scan, no specific column". We render that
        # as "{sheet} (all columns)" rather than the ugly "{sheet}!*".
        if col == "*":
            location_label = f"{sheet} (all columns)"
        else:
            location_label = f"{sheet}!{col}"

        if unique == 0:
            # The worker is about to emit finished([]) and stop. Show a
            # clear message so the user knows nothing was checked because
            # there was nothing to check (vs. a silent no-op).
            self.statusBar().showMessage(
                f"No URLs found in {location_label}."
            )
            return

        self.statusBar().showMessage(
            f"Found {unique:,} unique URL{'s' if unique != 1 else ''} "
            f"in {location_label}. Checking…"
        )
        self._progress_bar.setRange(0, unique)
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("%v / %m  (%p%)")

    @Slot(dict)
    def _on_progress_update(self, payload: dict) -> None:
        checked = payload.get("checked", 0)
        total = payload.get("total", 0)
        ok = payload.get("ok", 0)
        broken = payload.get("broken", 0)
        blocked = payload.get("blocked", 0)
        eta = payload.get("eta_seconds", 0.0)

        if total > 0:
            if self._progress_bar.maximum() != total:
                self._progress_bar.setRange(0, total)
            self._progress_bar.setValue(checked)
        self._lbl_checked.setText(f"Checked: {checked} / {total}")
        self._lbl_ok.setText(f"OK: {ok}")
        self._lbl_broken.setText(f"Broken: {broken}")
        self._lbl_blocked.setText(f"Possibly blocked: {blocked}")
        self._lbl_eta.setText(f"ETA: {format_eta(eta)}")

    @Slot(list)
    def _on_worker_finished(self, enriched_results: list) -> None:
        self._results = enriched_results
        # Compute issue counts for the message.
        from ..models import Classification
        broken = sum(
            1 for e in enriched_results
            if e.result.classification == Classification.BROKEN
        )
        blocked = sum(
            1 for e in enriched_results
            if e.result.classification == Classification.POSSIBLY_BLOCKED
        )
        total = len(enriched_results)
        issues = broken + blocked

        # Make sure the progress bar reaches 100% even if we missed the
        # last update (e.g. dropped due to throttling).
        if self._progress_bar.maximum() > 0:
            self._progress_bar.setValue(self._progress_bar.maximum())
        self._lbl_eta.setText("ETA: —")

        self._set_state("completed")

        # Special case: the worker finished with zero results because the
        # selected column had no URLs. Don't claim victory — explain.
        if total == 0:
            self._log.info("Run completed: no URLs found")
            QMessageBox.information(
                self,
                "No URLs found",
                "The selected column doesn't contain any web URLs.\n\n"
                "Tips:\n"
                "  • Double-check you picked the right sheet and column.\n"
                "  • Make sure cells contain links starting with http:// or https://\n"
                "  • If your file uses bare domains like 'example.com', "
                "turn on \u201cTreat bare domains as https:// URLs\u201d in advanced settings.",
            )
            self.statusBar().showMessage("No URLs found in the selected column.")
            return

        if issues == 0:
            self._log.info("Run completed: %d URLs, all OK", total)
            QMessageBox.information(
                self,
                "Great news!",
                f"\u2705 No broken URLs found.\n"
                f"All {total:,} URL{'s' if total != 1 else ''} returned HTTP 200.",
            )
            self.statusBar().showMessage(
                f"Done — checked {total:,} URL{'s' if total != 1 else ''}, no issues."
            )
        else:
            self._log.info(
                "Run completed: %d URLs, %d broken, %d possibly blocked",
                total, broken, blocked,
            )
            # Friendly summary message with full counts and a clear next step.
            QMessageBox.information(
                self,
                "Check complete",
                f"\u2705 Checked {total:,} URL{'s' if total != 1 else ''}.\n\n"
                f"\u2022 Broken:           {broken:,}\n"
                f"\u2022 Possibly blocked: {blocked:,}\n\n"
                f"Click \u201cSave Results\u201d to write the report.",
            )
            self.statusBar().showMessage(
                f"Done — {issues:,} issue{'s' if issues != 1 else ''} found "
                f"in {total:,} URL{'s' if total != 1 else ''}. Click Save Results."
            )

    @Slot(str)
    def _on_worker_error(self, message: str) -> None:
        self._set_state("idle")
        self._log.error("Worker error: %s", message)
        # The worker formats most messages friendly already (Phase 4's
        # _friendly_excel_error). Add a closing line with a clear next
        # step regardless.
        QMessageBox.warning(
            self,
            "Something went wrong",
            f"{message}\n\n"
            "What to try:\n"
            "  • Check the file isn't open in Excel\n"
            "  • Try again — many issues are temporary\n"
            "  • Try with a smaller test file to narrow down the cause",
        )
        self.statusBar().showMessage("Run failed. See message above.")

    @Slot()
    def _on_worker_canceled(self) -> None:
        self._set_state("idle")
        self._cancel_btn.setText("Cancel")
        self._cancel_btn.setEnabled(True)
        self.statusBar().showMessage("Cancelled.")
        QMessageBox.information(self, "Cancelled", "The run was cancelled.")

    @Slot()
    def _on_thread_finished(self) -> None:
        # Safe place to release the reference. The worker object will be
        # GC'd; signals on it have already fired.
        self._worker = None

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _set_state(self, state: str) -> None:
        self._state = state
        running = state == "running"
        completed = state == "completed"

        # Inputs locked during a run.
        self._drop_zone.setEnabled(not running)
        self._sheet_combo.setEnabled(not running and bool(self._sheets))
        self._column_combo.setEnabled(not running
                                      and self._column_combo.count() > 0)
        self._concurrency_spin.setEnabled(not running)
        self._timeout_spin.setEnabled(not running)
        self._retries_spin.setEnabled(not running)
        self._delay_spin.setEnabled(not running)
        self._header_row_spin.setEnabled(not running)
        self._auto_https_check.setEnabled(not running)
        self._check_btn.setEnabled(not running)
        # Loading-state label so the button itself communicates the state.
        self._check_btn.setText("Checking…" if running else "Check URLs")

        # Cancel only visible/enabled during a run.
        self._cancel_btn.setVisible(running)
        if running:
            self._cancel_btn.setText("Cancel")
            self._cancel_btn.setEnabled(True)

        # Save only enabled after completion with non-empty results.
        self._save_btn.setEnabled(completed and bool(self._results))
        # Show-in-folder gets re-enabled on save success; reset here so
        # starting a new run doesn't keep an obsolete pointer hot.
        if running:
            self._show_btn.setEnabled(False)

    def _reset_progress_ui(self) -> None:
        self._progress_bar.setRange(0, 0)  # indeterminate until total known
        self._progress_bar.setFormat("%p%")
        self._progress_bar.setValue(0)
        self._lbl_checked.setText("Checked: 0 / 0")
        self._lbl_ok.setText("OK: 0")
        self._lbl_broken.setText("Broken: 0")
        self._lbl_blocked.setText("Possibly blocked: 0")
        self._lbl_eta.setText("ETA: —")
        self._results = None

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _restore_settings(self) -> None:
        """Repopulate the UI from QSettings on startup.

        Called after _build_ui so widget references exist. Order:
        1) Engine spinboxes — always set, since they have safe defaults.
        2) Header row + auto-https — always set.
        3) Last file — load if it still exists. This implicitly populates
           the sheet/column combos via _on_file_chosen, after which we can
           also restore the last sheet/column choice.
        """
        eng = self._app_settings.engine_settings()
        self._concurrency_spin.setValue(eng.concurrency)
        self._timeout_spin.setValue(eng.timeout)
        self._retries_spin.setValue(eng.retries)
        self._delay_spin.setValue(eng.per_domain_delay)
        self._header_row_spin.setValue(self._app_settings.last_header_row())
        self._auto_https_check.setChecked(self._app_settings.last_auto_https())

        last_file = self._app_settings.last_file()
        if last_file is not None:
            # Load it. After loading, prefer the user's last sheet/column
            # over the auto-pick result.
            try:
                self._on_file_chosen(str(last_file), restoring=True)
            except Exception as e:  # noqa: BLE001
                # Don't let a bad last-file path stop the app from launching.
                self._log.warning("Could not restore last file %s: %s", last_file, e)

    def _save_settings(self) -> None:
        """Persist current values. Safe to call repeatedly."""
        self._app_settings.set_engine_settings(
            concurrency=self._concurrency_spin.value(),
            timeout=self._timeout_spin.value(),
            retries=self._retries_spin.value(),
            per_domain_delay=self._delay_spin.value(),
        )
        self._app_settings.set_last_header_row(self._header_row_spin.value())
        self._app_settings.set_last_auto_https(self._auto_https_check.isChecked())
        if self._excel_path is not None:
            self._app_settings.set_last_file(self._excel_path)
        sheet = self._sheet_combo.currentText()
        if sheet:
            self._app_settings.set_last_sheet(sheet)
        col_data = self._column_combo.currentData()
        if col_data and "column" in col_data:
            self._app_settings.set_last_column(col_data["column"])

    # ------------------------------------------------------------------
    # Misc slots
    # ------------------------------------------------------------------

    @Slot()
    def _on_show_in_folder_clicked(self) -> None:
        """Open the folder containing the most recently-saved report."""
        if self._last_saved_report is None or not self._last_saved_report.exists():
            self._show_error(
                "No saved report",
                "No report has been saved yet, or the file has been moved.",
            )
            return
        folder = self._last_saved_report.parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _show_error(self, title: str, message: str) -> None:
        QMessageBox.warning(self, title, message)
        self._log.warning("UI error shown — %s: %s", title, message)

    def closeEvent(self, event) -> None:  # noqa: N802
        """Block close while a run is in progress (with a confirm prompt).

        If the user really wants to abort, we cancel and wait briefly for
        the worker to settle before letting the window close.

        Always persists settings on close (so spinbox tweaks aren't lost
        if the user closes without ever clicking Check URLs).
        """
        if self._state == "running" and self._worker is not None:
            choice = QMessageBox.question(
                self,
                "Run in progress",
                "A run is still in progress. Cancel and quit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if choice != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._worker.request_cancel()
            self._worker.wait(3000)
        # Persist settings on every close.
        try:
            self._save_settings()
        except Exception:  # noqa: BLE001
            self._log.exception("Failed to save settings on close")
        self._log.info("Application closed")
        event.accept()
