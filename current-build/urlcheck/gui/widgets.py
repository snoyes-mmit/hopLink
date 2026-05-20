"""Small reusable widgets for the GUI.

Kept separate from main_window.py so it stays readable.

Components:
  - DropZone        — three-state drag/drop zone for .xlsx files
  - CollapsiblePanel — show/hide content section behind a toggle button
  - format_eta      — pure-function ETA formatter
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class DropZone(QFrame):
    """A labeled drop target for .xlsx files with three visual states.

    States:
      idle      — neutral dashed outline, instruction text
      hover     — blue dashed outline, "Drop to load" text (during drag)
      invalid   — red dashed outline, "Only .xlsx supported" text
                  (auto-clears back to idle after a short delay)

    Interactions:
      - Drag-and-drop a .xlsx file → emits file_dropped(path)
      - Click anywhere on the zone → emits browse_requested
        (single click target = less to learn than a drop zone PLUS
         a separate Browse button)
      - Drag a non-xlsx file or non-file payload → flashes the invalid
        state for ~2 s, no signal emitted

    The whole zone is clickable to remove the cognitive load of
    "is this a button or a drop zone?". Discoverability is helped by
    a tiny "Browse…" hint label in the corner.
    """

    file_dropped = Signal(str)
    browse_requested = Signal()

    # State strings — stable identifiers for tests/diagnostics.
    STATE_IDLE = "idle"
    STATE_HOVER = "hover"
    STATE_INVALID = "invalid"
    STATE_LOADED = "loaded"

    INSTRUCTION_TEXT = (
        "Drag and drop your Excel file here\nor click to browse"
    )
    HOVER_TEXT = "Drop to load this file"
    INVALID_TEXT = "Only .xlsx files are supported.\nSave older formats as .xlsx in Excel first."

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._state = self.STATE_IDLE
        self._loaded_path: Optional[Path] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        self._label = QLabel(self.INSTRUCTION_TEXT)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        self._label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self._label)

        # A subtle "Browse…" affordance in the corner so users who don't
        # think to click realize the whole area is clickable.
        hint_row = QHBoxLayout()
        hint_row.addStretch(1)
        self._hint = QLabel("Browse…")
        self._hint.setStyleSheet(
            "color: #305496; font-size: 11px; text-decoration: underline;"
        )
        hint_row.addWidget(self._hint)
        layout.addLayout(hint_row)

        # Timer to auto-clear the invalid state.
        self._invalid_timer = QTimer(self)
        self._invalid_timer.setSingleShot(True)
        self._invalid_timer.setInterval(2000)
        self._invalid_timer.timeout.connect(self._reset_to_idle_after_invalid)

        self._apply_style(self.STATE_IDLE)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_file(self, path: Optional[str]) -> None:
        """Update the visible label after a file is selected (or cleared)."""
        if path:
            self._loaded_path = Path(path)
            self._label.setText(
                f"<b>Selected:</b> {self._loaded_path.name}\n"
                f"<span style='color:#666; font-size:11px;'>{path}</span>"
            )
            # Allow rich text for the bold/grey styling.
            self._label.setTextFormat(Qt.TextFormat.RichText)
            self._apply_style(self.STATE_LOADED)
            self._hint.setText("Drop a different file, or click to browse")
        else:
            self._loaded_path = None
            self._label.setTextFormat(Qt.TextFormat.PlainText)
            self._label.setText(self.INSTRUCTION_TEXT)
            self._apply_style(self.STATE_IDLE)
            self._hint.setText("Browse…")

    @property
    def state(self) -> str:
        return self._state

    # ------------------------------------------------------------------
    # Click → browse
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.browse_requested.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    # ------------------------------------------------------------------
    # Drag/drop event overrides
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        path = self._extract_xlsx_path(event)
        if path is not None:
            event.acceptProposedAction()
            self._apply_style(self.STATE_HOVER)
            self._label.setTextFormat(Qt.TextFormat.PlainText)
            self._label.setText(self.HOVER_TEXT)
        else:
            # Reject + brief invalid-state flash so user understands why
            # nothing happened.
            event.ignore()
            self._show_invalid()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        # Restore previous state. If we were showing invalid, let its
        # timer finish; otherwise revert to idle/loaded.
        if self._state == self.STATE_HOVER:
            self._restore_resting_state()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        path = self._extract_xlsx_path(event)
        if path is None:
            event.ignore()
            self._show_invalid()
            return
        event.acceptProposedAction()
        # Don't change state here; main_window will call set_file()
        # with the final styling.
        self.file_dropped.emit(path)

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def _show_invalid(self) -> None:
        """Show the invalid state and schedule auto-revert."""
        self._apply_style(self.STATE_INVALID)
        self._label.setTextFormat(Qt.TextFormat.PlainText)
        self._label.setText(self.INVALID_TEXT)
        self._invalid_timer.start()

    def _reset_to_idle_after_invalid(self) -> None:
        if self._state == self.STATE_INVALID:
            self._restore_resting_state()

    def _restore_resting_state(self) -> None:
        if self._loaded_path is not None:
            self.set_file(str(self._loaded_path))
        else:
            self.set_file(None)

    def _apply_style(self, state: str) -> None:
        self._state = state
        styles = {
            self.STATE_IDLE: (
                "QFrame { border: 2px dashed #b0b0b0; border-radius: 8px; "
                "background-color: #fafafa; }"
            ),
            self.STATE_HOVER: (
                "QFrame { border: 2px dashed #305496; border-radius: 8px; "
                "background-color: #eef3fa; }"
            ),
            self.STATE_INVALID: (
                "QFrame { border: 2px dashed #c0392b; border-radius: 8px; "
                "background-color: #fdecea; }"
            ),
            self.STATE_LOADED: (
                "QFrame { border: 2px solid #2e7d32; border-radius: 8px; "
                "background-color: #f1f8e9; }"
            ),
        }
        self.setStyleSheet(styles.get(state, styles[self.STATE_IDLE]))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_xlsx_path(event) -> Optional[str]:
        mime = event.mimeData()
        if not mime.hasUrls():
            return None
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            local = url.toLocalFile()
            if local.lower().endswith(".xlsx"):
                return local
        return None


class CollapsiblePanel(QWidget):
    """A simple show/hide content section behind a toggle button.

    Qt has no first-class "expander" widget, so we build the smallest
    thing that works: a QToolButton with an arrow indicator that toggles
    a child widget's visibility.
    """

    def __init__(
        self,
        title: str,
        parent: Optional[QWidget] = None,
        initially_expanded: bool = False,
    ) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        self._toggle = QToolButton()
        self._toggle.setText(title)
        self._toggle.setCheckable(True)
        self._toggle.setChecked(initially_expanded)
        self._toggle.setStyleSheet("QToolButton { border: none; font-weight: 600; }")
        self._toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toggle.setArrowType(
            Qt.ArrowType.DownArrow if initially_expanded else Qt.ArrowType.RightArrow
        )
        self._toggle.clicked.connect(self._on_toggled)
        outer.addWidget(self._toggle)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(16, 4, 4, 4)
        self._content.setVisible(initially_expanded)
        outer.addWidget(self._content)

    def add_widget(self, widget: QWidget) -> None:
        self._content_layout.addWidget(widget)

    def add_layout(self, layout) -> None:
        self._content_layout.addLayout(layout)

    def _on_toggled(self, checked: bool) -> None:
        self._content.setVisible(checked)
        self._toggle.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )


def format_eta(seconds: float) -> str:
    """HH:MM:SS for ETAs >= 1 hour, MM:SS otherwise. '—' for 0 / unknown."""
    if seconds is None or seconds <= 0:
        return "—"
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
