"""Drag-and-drop zone widget for folder selection."""
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QFileDialog, QStackedWidget, QSizePolicy


class DropZone(QFrame):
    """A widget that accepts folder drops and clicks to browse."""

    folder_dropped = Signal(Path)
    file_dropped = Signal(Path)

    def __init__(self, label: str, allow_file_mode: bool = False, parent=None):
        super().__init__(parent)
        self._label_text = label
        self._allow_file_mode = allow_file_mode
        self._file_mode = False
        self._folder_path: Path | None = None
        self._file_path: Path | None = None
        self._setup_ui()
        self.setAcceptDrops(True)

    def _setup_ui(self) -> None:
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #666;
                border-radius: 8px;
                background-color: #2a2a2a;
                min-height: 80px;
            }
            DropZone:hover {
                border-color: #888;
                background-color: #333;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._title_label = QLabel(self._label_text)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet("font-weight: bold; font-size: 14px;")

        self._hint_label = QLabel("Drop folder here\nor click to browse")
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_label.setStyleSheet("color: #888;")

        self._path_label = QLabel("")
        self._path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._path_label.setStyleSheet("color: #4a9eff;")
        self._path_label.setWordWrap(True)

        self._content_stack = QStackedWidget()
        self._content_stack.addWidget(self._hint_label)
        self._content_stack.addWidget(self._path_label)
        self._content_stack.setCurrentIndex(0)

        layout.addWidget(self._title_label)
        layout.addWidget(self._content_stack)

    def set_file_mode(self, enabled: bool, file_mode_title: str | None = None) -> None:
        """Set whether the drop zone accepts files instead of folders."""
        self._file_mode = enabled
        if enabled:
            self._title_label.setText(file_mode_title or "OCR Dump File")
            self._hint_label.setText("Drop .toml file here\nor click to browse")
            if self._file_path:
                self._show_path(self._file_path)
                self.file_dropped.emit(self._file_path)
            else:
                self._clear_display()
        else:
            self._title_label.setText(self._label_text)
            self._hint_label.setText("Drop folder here\nor click to browse")
            if self._folder_path:
                self._show_path(self._folder_path)
                self.folder_dropped.emit(self._folder_path)
            else:
                self._clear_display()

    def is_file_mode(self) -> bool:
        return self._file_mode

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                path = Path(urls[0].toLocalFile())
                if self._file_mode:
                    if path.is_file() and path.suffix == ".toml":
                        event.acceptProposedAction()
                        self.setStyleSheet(self.styleSheet().replace("#2a2a2a", "#3a3a4a"))
                        return
                else:
                    if path.is_dir():
                        event.acceptProposedAction()
                        self.setStyleSheet(self.styleSheet().replace("#2a2a2a", "#3a3a4a"))
                        return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self.setStyleSheet(self.styleSheet().replace("#3a3a4a", "#2a2a2a"))

    def dropEvent(self, event: QDropEvent) -> None:
        self.setStyleSheet(self.styleSheet().replace("#3a3a4a", "#2a2a2a"))
        urls = event.mimeData().urls()
        if urls:
            path = Path(urls[0].toLocalFile())
            if self._file_mode:
                if path.is_file() and path.suffix == ".toml":
                    self._set_file(path)
                    event.acceptProposedAction()
            else:
                if path.is_dir():
                    self._set_folder(path)
                    event.acceptProposedAction()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self._file_mode:
                current = self.get_file()
                start_dir = str(current.parent) if current and current.exists() else str(Path.home())
                file_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Select OCR Dump File",
                    start_dir,
                    "TOML files (*.toml)",
                )
                if file_path:
                    self._set_file(Path(file_path))
            else:
                current = self.get_folder()
                start_dir = str(current) if current and current.exists() else str(Path.home())
                folder = QFileDialog.getExistingDirectory(
                    self,
                    f"Select {self._label_text} Folder",
                    start_dir,
                )
                if folder:
                    self._set_folder(Path(folder))

    def _show_path(self, path: Path) -> None:
        self._path_label.setText(str(path))
        self._content_stack.setCurrentWidget(self._path_label)

    def _clear_display(self) -> None:
        self._path_label.setText("")
        self._content_stack.setCurrentWidget(self._hint_label)

    def _set_folder(self, path: Path) -> None:
        self._folder_path = path
        self._show_path(path)
        self.folder_dropped.emit(path)

    def _set_file(self, path: Path) -> None:
        self._file_path = path
        self._show_path(path)
        self.file_dropped.emit(path)

    def clear(self) -> None:
        self._folder_path = None
        self._file_path = None
        self._clear_display()

    def get_folder(self) -> Path | None:
        return self._folder_path

    def get_file(self) -> Path | None:
        return self._file_path

    def set_remembered_file(self, path: Path) -> None:
        """Store a file path without displaying or emitting signal.

        Used to restore saved state - the path will be shown when file mode is toggled on.
        """
        self._file_path = path
