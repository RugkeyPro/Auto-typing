from __future__ import annotations

import sys

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSlider,
    QStyle,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .controller import AutoTyperController
from .core import TypingProgress, TypingState
from .hotkeys import GlobalHotkeyManager, HotkeyError
from .input_blocker import InputBlockerError, default_input_blocker
from .logging_setup import setup_logging
from .permissions import check_accessibility, is_macos
from .text_io import read_text_file
from .typing_backend import default_backend


class HotkeyBridge(QObject):
    start_requested = Signal()
    pause_requested = Signal()


class ProgressBridge(QObject):
    progress_changed = Signal(object)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MacAutoTyper")
        self.resize(860, 640)

        self._progress_bridge = ProgressBridge()
        self._progress_bridge.progress_changed.connect(self._apply_progress)

        self._hotkey_bridge = HotkeyBridge()
        self._hotkey_bridge.start_requested.connect(self._start_or_resume)
        self._hotkey_bridge.pause_requested.connect(self._pause)

        self._input_blocker = default_input_blocker(
            self._hotkey_bridge.pause_requested.emit,
            self._hotkey_bridge.start_requested.emit,
        )

        self._controller = AutoTyperController(
            default_backend(),
            on_progress=self._progress_bridge.progress_changed.emit,
            input_blocker=self._input_blocker,
        )

        self._hotkeys = GlobalHotkeyManager(
            self._hotkey_bridge.start_requested.emit,
            self._hotkey_bridge.pause_requested.emit,
        )

        self._quitting = False
        self._tray_icon: QSystemTrayIcon | None = None
        self._tray_start_action: QAction | None = None
        self._tray_pause_action: QAction | None = None
        self._build_ui()
        self._build_tray()
        if self._tray_icon is None:
            self.hide_button.setEnabled(False)
        self._connect_ui()
        self._refresh_permission_status(prompt=False)
        self._start_input_blocker()
        self._start_hotkeys()
        self._apply_progress(self._controller.snapshot())

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._controller.shutdown()
        self._hotkeys.stop()
        self._input_blocker.stop()
        super().closeEvent(event)

    def _build_ui(self) -> None:
        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("MacAutoTyper")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMinimumWidth(120)
        self.status_label.setFixedHeight(26)
        header.addWidget(title, 1)
        header.addWidget(self.status_label, 0, Qt.AlignRight | Qt.AlignVCenter)
        layout.addLayout(header)

        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.setPlaceholderText("Paste or type the text to auto-enter here.")
        layout.addWidget(self.editor, 1)

        controls = QFrame()
        controls.setObjectName("controlsFrame")
        grid = QGridLayout(controls)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        self.import_button = QPushButton("Import TXT/MD")
        self.import_button.setObjectName("importButton")
        self.start_button = QPushButton("Start / Resume")
        self.start_button.setObjectName("startButton")
        self.pause_button = QPushButton("Pause")
        self.pause_button.setObjectName("pauseButton")
        self.reset_button = QPushButton("Reset Progress")
        self.reset_button.setObjectName("resetButton")
        self.clear_button = QPushButton("Clear Text")
        self.clear_button.setObjectName("clearButton")
        self.permission_button = QPushButton("Check macOS Permission")
        self.permission_button.setObjectName("permissionButton")
        self.hide_button = QPushButton("Minimize")
        self.hide_button.setObjectName("hideButton")

        grid.addWidget(self.import_button, 0, 0)
        grid.addWidget(self.start_button, 0, 1)
        grid.addWidget(self.pause_button, 0, 2)
        grid.addWidget(self.reset_button, 0, 3)
        grid.addWidget(self.clear_button, 0, 4)
        grid.addWidget(self.hide_button, 0, 5)

        speed_label = QLabel("Delay")
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(20, 800)
        self.speed_slider.setSingleStep(10)
        self.speed_slider.setValue(120)
        self.speed_value_label = QLabel("120 ms/char")
        self.speed_value_label.setObjectName("speedValueLabel")
        self.jitter_checkbox = QCheckBox("Natural rhythm")
        self.jitter_checkbox.setChecked(True)

        grid.addWidget(speed_label, 1, 0)
        grid.addWidget(self.speed_slider, 1, 1, 1, 2)
        grid.addWidget(self.speed_value_label, 1, 3)
        grid.addWidget(self.jitter_checkbox, 1, 4, 1, 2)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.position_label = QLabel("0 / 0")
        self.position_label.setObjectName("positionLabel")
        grid.addWidget(self.progress_bar, 2, 0, 1, 5)
        grid.addWidget(self.position_label, 2, 5)

        self.permission_label = QLabel("")
        self.permission_label.setObjectName("permissionLabel")
        self.permission_label.setWordWrap(True)
        grid.addWidget(self.permission_button, 3, 0)
        grid.addWidget(self.permission_label, 3, 1, 1, 5)

        layout.addWidget(controls)

        footer = QLabel("Global hotkeys: Ctrl+1 start/resume, Ctrl+2 pause")
        footer.setObjectName("footerLabel")
        layout.addWidget(footer)

        self.setCentralWidget(root)
        self._apply_styles()

        open_action = QAction("Import", self)
        open_action.triggered.connect(self._import_text)
        self.addAction(open_action)

    def _connect_ui(self) -> None:
        self.editor.textChanged.connect(self._editor_changed)
        self.import_button.clicked.connect(self._import_text)
        self.start_button.clicked.connect(self._start_or_resume)
        self.pause_button.clicked.connect(self._pause)
        self.reset_button.clicked.connect(self._reset_progress)
        self.clear_button.clicked.connect(self._clear_text)
        self.hide_button.clicked.connect(self.showMinimized)
        self.permission_button.clicked.connect(lambda: self._check_permissions(prompt=True))
        self.speed_slider.valueChanged.connect(self._speed_changed)
        self.jitter_checkbox.toggled.connect(self._controller.set_jitter_enabled)

    def _build_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self._tray_icon = QSystemTrayIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon),
            self,
        )
        menu = QMenu(self)

        show_action = QAction("Show Setup", self)
        show_action.triggered.connect(self._show_from_tray)
        self._tray_start_action = QAction("Start / Resume", self)
        self._tray_start_action.triggered.connect(self._start_or_resume)
        self._tray_pause_action = QAction("Pause", self)
        self._tray_pause_action.triggered.connect(self._pause)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_from_tray)

        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(self._tray_start_action)
        menu.addAction(self._tray_pause_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self._tray_icon.setContextMenu(menu)
        self._tray_icon.activated.connect(self._tray_activated)
        self._tray_icon.show()

    def _show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_from_tray()

    def _quit_from_tray(self) -> None:
        self._quitting = True
        self.close()

    def _start_input_blocker(self) -> None:
        try:
            self._input_blocker.start()
        except InputBlockerError as exc:
            self.permission_label.setText(str(exc))

    def _check_permissions(self, prompt: bool) -> None:
        self._refresh_permission_status(prompt=prompt)
        self._start_input_blocker()

    def _start_hotkeys(self) -> None:
        if is_macos():
            return
        try:
            self._hotkeys.start()
        except HotkeyError as exc:
            self.status_label.setText("Hotkeys unavailable")
            self.permission_label.setText(str(exc))

    def _refresh_permission_status(self, prompt: bool) -> None:
        ok, message = check_accessibility(prompt=prompt)
        self.permission_label.setText(message)
        if is_macos() and not ok and prompt:
            QMessageBox.information(
                self,
                "macOS Permission",
                "Open System Settings and allow Accessibility/Input Monitoring for MacAutoTyper.",
            )

    def _editor_changed(self) -> None:
        self._controller.set_text(self.editor.toPlainText(), keep_position=True)

    def _import_text(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import text",
            "",
            "Text files (*.txt *.md);;All files (*.*)",
        )
        if not path:
            return
        try:
            text = read_text_file(path)
        except OSError as exc:
            QMessageBox.warning(self, "Import failed", str(exc))
            return

        self.editor.blockSignals(True)
        self.editor.setPlainText(text)
        self.editor.blockSignals(False)
        self._controller.set_text(text, keep_position=False)

    def _start_or_resume(self) -> None:
        self._controller.set_text(self.editor.toPlainText(), keep_position=True)
        self._controller.start_or_resume()

    def _pause(self) -> None:
        self._controller.pause()

    def _reset_progress(self) -> None:
        self._controller.set_text(self.editor.toPlainText(), keep_position=True)
        self._controller.reset()

    def _clear_text(self) -> None:
        self.editor.blockSignals(True)
        self.editor.clear()
        self.editor.blockSignals(False)
        self._controller.clear()

    def _speed_changed(self, value: int) -> None:
        self.speed_value_label.setText(f"{value} ms/char")
        self._controller.set_delay_ms(value)

    def _apply_progress(self, progress: TypingProgress) -> None:
        self.progress_bar.setRange(0, max(1, progress.total))
        self.progress_bar.setValue(min(progress.position, progress.total))
        self.position_label.setText(f"{progress.position} / {progress.total}")
        self.status_label.setText(self._status_text(progress))

        state_str = progress.state.value
        self.status_label.setProperty("state", state_str)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

        self.editor.setEnabled(True)
        self.editor.setReadOnly(progress.state == TypingState.RUNNING)
        self.import_button.setEnabled(progress.state != TypingState.RUNNING)
        self.start_button.setEnabled(progress.total > 0 and progress.state != TypingState.RUNNING)
        self.pause_button.setEnabled(progress.state == TypingState.RUNNING)
        self.reset_button.setEnabled(progress.total > 0 and progress.state != TypingState.RUNNING)
        self.clear_button.setEnabled(progress.state != TypingState.RUNNING)
        if self._tray_icon is not None:
            self._tray_icon.setToolTip(
                f"MacAutoTyper - {self._status_text(progress)} ({progress.position}/{progress.total})"
            )
        if self._tray_start_action is not None:
            self._tray_start_action.setEnabled(progress.total > 0 and progress.state != TypingState.RUNNING)
        if self._tray_pause_action is not None:
            self._tray_pause_action.setEnabled(progress.state == TypingState.RUNNING)

    def _status_text(self, progress: TypingProgress) -> str:
        if progress.state == TypingState.IDLE:
            return "Ready"
        if progress.state == TypingState.RUNNING:
            return "Typing"
        if progress.state == TypingState.PAUSED:
            return "Paused"
        if progress.state == TypingState.COMPLETED:
            return "Completed"
        if progress.state == TypingState.ERROR:
            return f"Error: {progress.last_error}"
        return progress.state.value

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f8fafc;
            }
            
            QLabel#titleLabel {
                color: #0f172a;
                font-size: 20px;
                font-weight: 700;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                letter-spacing: -0.2px;
            }
            
            QLabel#footerLabel {
                color: #64748b;
                font-size: 12px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                padding-left: 2px;
            }
            
            QTextEdit {
                background-color: #ffffff;
                color: #334155;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                line-height: 1.5;
            }
            
            QTextEdit:focus {
                border: 1px solid #3b82f6;
            }
            
            QFrame#controlsFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
            
            /* Status Badge dynamic styling */
            QLabel#statusLabel {
                font-size: 11px;
                font-weight: 700;
                border-radius: 4px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            QLabel#statusLabel[state="idle"] {
                color: #64748b;
                background-color: #f1f5f9;
                border: 1px solid #cbd5e1;
            }
            QLabel#statusLabel[state="running"] {
                color: #15803d;
                background-color: #dcfce7;
                border: 1px solid #bbf7d0;
            }
            QLabel#statusLabel[state="paused"] {
                color: #b45309;
                background-color: #fef3c7;
                border: 1px solid #fde68a;
            }
            QLabel#statusLabel[state="completed"] {
                color: #1d4ed8;
                background-color: #dbeafe;
                border: 1px solid #bfdbfe;
            }
            QLabel#statusLabel[state="error"] {
                color: #b91c1c;
                background-color: #fee2e2;
                border: 1px solid #fecaca;
            }
            
            /* Buttons Styling */
            QPushButton {
                min-height: 32px;
                padding: 4px 14px;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                background-color: #ffffff;
                color: #475569;
                font-weight: 500;
                font-size: 13px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            
            QPushButton:hover {
                background-color: #f8fafc;
                border-color: #cbd5e1;
                color: #1e293b;
            }
            
            QPushButton:pressed {
                background-color: #f1f5f9;
            }
            
            QPushButton:disabled {
                color: #94a3b8;
                background-color: #f8fafc;
                border-color: #e2e8f0;
            }
            
            /* Primary CTA button (Start) */
            QPushButton#startButton {
                background-color: #2563eb;
                border: none;
                color: #ffffff;
                font-weight: 600;
            }
            
            QPushButton#startButton:hover {
                background-color: #1d4ed8;
            }
            
            QPushButton#startButton:pressed {
                background-color: #1e40af;
            }
            
            QPushButton#startButton:disabled {
                background-color: #bfdbfe;
                color: #ffffff;
            }
            
            /* Danger action button (Pause) */
            QPushButton#pauseButton {
                background-color: #ef4444;
                border: none;
                color: #ffffff;
                font-weight: 600;
            }
            
            QPushButton#pauseButton:hover {
                background-color: #dc2626;
            }
            
            QPushButton#pauseButton:pressed {
                background-color: #b91c1c;
            }
            
            QPushButton#pauseButton:disabled {
                background-color: #fca5a5;
                color: #ffffff;
            }
            
            /* Secondary reset/clear buttons */
            QPushButton#resetButton:hover, QPushButton#clearButton:hover {
                border-color: #f59e0b;
                color: #d97706;
            }
            
            /* Slider Styling */
            QSlider::groove:horizontal {
                height: 4px;
                background: #e2e8f0;
                border-radius: 2px;
            }
            
            QSlider::sub-page:horizontal {
                background: #2563eb;
                border-radius: 2px;
            }
            
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 2px solid #2563eb;
                width: 14px;
                height: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }
            
            QSlider::handle:horizontal:hover {
                background: #2563eb;
            }
            
            /* Progress Bar Styling */
            QProgressBar {
                min-height: 8px;
                max-height: 8px;
                border: none;
                border-radius: 4px;
                background: #e2e8f0;
                text-align: center;
                color: transparent;
            }
            
            QProgressBar::chunk {
                background: #2563eb;
                border-radius: 4px;
            }
            
            /* General Label custom styles */
            QLabel {
                color: #475569;
                font-size: 13px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            
            QLabel#positionLabel {
                color: #1e293b;
                font-weight: 600;
                font-family: monospace;
            }
            
            QLabel#speedValueLabel {
                color: #2563eb;
                font-weight: 600;
            }
            
            QLabel#permissionLabel {
                color: #94a3b8;
                font-size: 12px;
            }
            
            /* Checkbox Styling */
            QCheckBox {
                color: #475569;
                font-size: 13px;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QCheckBox::indicator:hover {
                border-color: #2563eb;
            }
            QCheckBox::indicator:checked {
                background-color: #2563eb;
                border-color: #2563eb;
            }
            """
        )


def run(argv: list[str] | None = None) -> int:
    setup_logging()
    app = QApplication(argv or sys.argv)
    app.setApplicationName("MacAutoTyper")
    app.setQuitOnLastWindowClosed(True)
    window = MainWindow()
    window.show()
    return app.exec()
