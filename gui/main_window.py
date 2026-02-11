"""Main application window."""
from datetime import datetime
from pathlib import Path

import tomli_w
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QFileDialog,
    QMessageBox,
)

from image_analyzer import ScreenshotFilename
from settings import load_settings, save_settings
from gui.drop_zone import DropZone
from gui.file_list import FileListWidget
from gui.workers import ScreenshotWorker, ConversionWorker
from gui.settings_dialog import SettingsDialog, load_api_key


class MainWindow(QMainWindow):
    """Main application window with drag-drop zones and conversion controls."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hand History De-anonymizer")
        self.setMinimumSize(800, 600)

        self._screenshots_folder: Path | None = None
        self._hands_folder: Path | None = None
        self._output_folder: Path | None = None
        self._screenshot_worker: ScreenshotWorker | None = None
        self._conversion_worker: ConversionWorker | None = None
        self._hand_data: dict[str, dict[int, str]] = {}

        self._setup_menu()
        self._setup_ui()
        self._load_saved_folders()
        self._update_convert_button()

    def _setup_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")

        settings_action = QAction("Settings...", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        drop_layout = QHBoxLayout()
        self._screenshots_drop = DropZone("Screenshots")
        self._screenshots_drop.folder_dropped.connect(self._on_screenshots_folder_changed)
        self._hands_drop = DropZone("Hand Files")
        self._hands_drop.folder_dropped.connect(self._on_hands_folder_changed)
        drop_layout.addWidget(self._screenshots_drop)
        drop_layout.addWidget(self._hands_drop)
        layout.addLayout(drop_layout)

        lists_layout = QHBoxLayout()
        self._screenshots_list = FileListWidget(
            "Screenshots",
            validator=ScreenshotFilename.is_valid,
        )
        self._screenshots_list.refresh_clicked.connect(self._refresh_screenshots)
        self._hands_list = FileListWidget("Hand Files")
        self._hands_list.refresh_clicked.connect(self._refresh_hands)
        lists_layout.addWidget(self._screenshots_list)
        lists_layout.addWidget(self._hands_list)
        layout.addLayout(lists_layout)

        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output:"))
        self._output_input = QLineEdit()
        self._output_input.setPlaceholderText("Select output folder...")
        self._output_input.textChanged.connect(self._on_output_changed)
        output_layout.addWidget(self._output_input)
        self._output_browse_btn = QPushButton("Browse...")
        self._output_browse_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(self._output_browse_btn)
        layout.addLayout(output_layout)

        self._screenshots_progress_label = QLabel("Step 1: Extracting player names")
        self._screenshots_progress_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(self._screenshots_progress_label)

        self._screenshots_progress_bar = QProgressBar()
        self._screenshots_progress_bar.setValue(0)
        layout.addWidget(self._screenshots_progress_bar)

        self._conversion_progress_label = QLabel("Step 2: Converting hand histories")
        self._conversion_progress_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(self._conversion_progress_label)

        self._conversion_progress_bar = QProgressBar()
        self._conversion_progress_bar.setValue(0)
        layout.addWidget(self._conversion_progress_bar)

        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet("color: #888;")
        layout.addWidget(self._status_label)

        log_label = QLabel("Log")
        log_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(log_label)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                border: 1px solid #444;
                border-radius: 4px;
                font-family: monospace;
            }
        """)
        layout.addWidget(self._log)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self._convert_btn = QPushButton("Convert")
        self._convert_btn.setMinimumWidth(100)
        self._convert_btn.clicked.connect(self._start_conversion)
        button_layout.addWidget(self._convert_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setMinimumWidth(100)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel_conversion)
        button_layout.addWidget(self._cancel_btn)

        layout.addLayout(button_layout)

    def _on_screenshots_folder_changed(self, path: Path) -> None:
        self._screenshots_folder = path
        self._screenshots_list.set_folder(path, "*.png")
        self._save_folder_setting("last_screenshots_folder", path)
        self._update_convert_button()

    def _on_hands_folder_changed(self, path: Path) -> None:
        self._hands_folder = path
        self._hands_list.set_folder(path, "*.txt")
        self._save_folder_setting("last_hands_folder", path)
        self._update_convert_button()

    def _on_output_changed(self, text: str) -> None:
        self._output_folder = Path(text) if text else None
        if self._output_folder:
            self._save_folder_setting("last_output_folder", self._output_folder)
        self._update_convert_button()

    def _save_folder_setting(self, key: str, path: Path) -> None:
        settings = load_settings()
        settings[key] = str(path)
        save_settings(settings)

    def _load_saved_folders(self) -> None:
        settings = load_settings()

        screenshots = settings.get("last_screenshots_folder", "")
        if screenshots and Path(screenshots).exists():
            self._screenshots_drop._set_folder(Path(screenshots))

        hands = settings.get("last_hands_folder", "")
        if hands and Path(hands).exists():
            self._hands_drop._set_folder(Path(hands))

        output = settings.get("last_output_folder", "")
        if output and Path(output).exists():
            self._output_input.setText(output)

    def _refresh_screenshots(self) -> None:
        if self._screenshots_folder:
            self._screenshots_list.set_folder(self._screenshots_folder, "*.png")
            self._update_convert_button()

    def _refresh_hands(self) -> None:
        if self._hands_folder:
            self._hands_list.set_folder(self._hands_folder, "*.txt")
            self._update_convert_button()

    def _browse_output(self) -> None:
        start_dir = str(self._output_folder) if self._output_folder and self._output_folder.exists() else str(Path.home())
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            start_dir,
        )
        if folder:
            self._output_input.setText(folder)

    def _update_convert_button(self) -> None:
        enabled = (
            self._screenshots_folder is not None
            and self._hands_folder is not None
            and self._output_folder is not None
            and self._screenshots_list.valid_count() > 0
            and self._hands_list.count() > 0
        )
        self._convert_btn.setEnabled(enabled)

    def _show_settings(self) -> None:
        dialog = SettingsDialog(self)
        dialog.exec()

    def _start_conversion(self) -> None:
        api_key = load_api_key()
        if not api_key:
            result = QMessageBox.question(
                self,
                "API Key Required",
                "No API key configured. Would you like to open settings?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if result == QMessageBox.StandardButton.Yes:
                self._show_settings()
                api_key = load_api_key()
                if not api_key:
                    return
            else:
                return

        self._log.clear()
        self._hand_data = {}
        self._screenshots_progress_bar.setValue(0)
        self._conversion_progress_bar.setValue(0)
        self._set_processing_state(True)

        self._log.append("Step 1: Processing screenshots...\n")

        settings = load_settings()
        parallel_calls = settings.get("parallel_api_calls", 5)
        rate_limit = settings.get("api_rate_limit_per_minute", 50)

        self._screenshot_worker = ScreenshotWorker(
            self._screenshots_folder,
            api_key=api_key,
            parallel_calls=parallel_calls,
            rate_limit_per_minute=rate_limit,
        )
        self._screenshot_worker.progress.connect(self._on_screenshot_progress)
        self._screenshot_worker.result.connect(self._on_screenshot_result)
        self._screenshot_worker.error.connect(self._on_screenshot_error)
        self._screenshot_worker.finished_processing.connect(self._on_screenshots_done)
        self._screenshot_worker.start()

    def _cancel_conversion(self) -> None:
        if self._screenshot_worker and self._screenshot_worker.isRunning():
            self._screenshot_worker.cancel()
        if self._conversion_worker and self._conversion_worker.isRunning():
            self._conversion_worker.cancel()
        self._log.append("\n--- Cancelled ---")
        self._set_processing_state(False)

    def _set_processing_state(self, processing: bool) -> None:
        self._convert_btn.setEnabled(not processing)
        self._cancel_btn.setEnabled(processing)
        self._screenshots_drop.setEnabled(not processing)
        self._hands_drop.setEnabled(not processing)
        self._output_browse_btn.setEnabled(not processing)
        self._output_input.setEnabled(not processing)

    def _on_screenshot_progress(self, current: int, total: int, filename: str) -> None:
        self._screenshots_progress_bar.setMaximum(total)
        self._screenshots_progress_bar.setValue(current)
        self._status_label.setText(f"Processing: {filename} ({current}/{total})")

    def _on_screenshot_result(self, hand_number: str, filename: str, position_count: int, seat_count: int) -> None:
        self._log.append(f"  {filename} → #{hand_number}: {position_count} positions, {seat_count} seats")

    def _on_screenshot_error(self, filename: str, message: str) -> None:
        self._log.append(f"  Error ({filename}): {message}")

    def _write_ocr_debug_file(self, results: list[dict], errors: list[dict]) -> None:
        timestamp = datetime.now()
        filename = f"ocr_results_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.toml"
        path = self._output_folder / filename

        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "metadata": {
                "timestamp": timestamp.isoformat(),
                "screenshots_folder": str(self._screenshots_folder),
                "total_successful": len(results),
                "total_errors": len(errors),
            },
            "results": {
                r["hand_number"]: {
                    "filename": r["filename"],
                    "table_type": r["table_type"],
                    "positions": r["position_names"],
                }
                for r in sorted(results, key=lambda x: x["filename"])
            },
        }

        if errors:
            data["errors"] = {
                e["filename"]: e["error"]
                for e in sorted(errors, key=lambda x: x["filename"])
            }

        with open(path, "wb") as f:
            tomli_w.dump(data, f)

        self._log.append(f"OCR results saved to: {filename}")

    def _on_screenshots_done(self, data: tuple) -> None:
        hand_data, ocr_results, ocr_errors = data
        self._hand_data = hand_data
        self._log.append(f"\nExtracted data for {len(hand_data)} hands\n")

        self._write_ocr_debug_file(ocr_results, ocr_errors)

        if not hand_data:
            self._log.append("No screenshot data extracted. Nothing to convert.")
            self._set_processing_state(False)
            return

        self._log.append("Step 2: Converting hand histories...\n")

        self._conversion_worker = ConversionWorker(
            self._hands_folder,
            hand_data,
            self._output_folder,
        )
        self._conversion_worker.progress.connect(self._on_conversion_progress)
        self._conversion_worker.hand_converted.connect(self._on_hand_converted)
        self._conversion_worker.hand_skipped.connect(self._on_hand_skipped)
        self._conversion_worker.finished_processing.connect(self._on_conversion_done)
        self._conversion_worker.start()

    def _on_conversion_progress(self, current: int, total: int, filename: str) -> None:
        self._conversion_progress_bar.setMaximum(total)
        self._conversion_progress_bar.setValue(current)
        self._status_label.setText(f"Converting: {filename} ({current}/{total})")

    def _on_hand_converted(self, hand_number: str, player_count: int) -> None:
        self._log.append(f"  Hand #{hand_number}: {player_count} players matched")

    def _on_hand_skipped(self, hand_number: str, reason: str) -> None:
        self._log.append(f"  Skipped #{hand_number}: {reason}")

    def _on_conversion_done(self, success: int, failed: int) -> None:
        self._log.append(f"\n=== Summary ===")
        self._log.append(f"Converted: {success} hands")
        self._log.append(f"Skipped:   {failed} hands")
        self._log.append(f"\nOutput saved to: {self._output_folder}")

        self._status_label.setText("Done")
        self._conversion_progress_bar.setValue(self._conversion_progress_bar.maximum())
        self._set_processing_state(False)

        QMessageBox.information(
            self,
            "Conversion Complete",
            f"Converted {success} hands.\nSkipped {failed} hands.\n\n"
            f"Output saved to:\n{self._output_folder}",
        )
