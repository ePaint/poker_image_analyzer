"""Drag-and-drop zone widget for folder selection."""
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QFileDialog


class DropZone(QFrame):
    """A widget that accepts folder drops and clicks to browse."""

    folder_dropped = Signal(Path)

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._label_text = label
        self._setup_ui()
        self.setAcceptDrops(True)

    def _setup_ui(self) -> None:
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
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
        self._path_label.hide()

        layout.addWidget(self._title_label)
        layout.addWidget(self._hint_label)
        layout.addWidget(self._path_label)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                path = Path(urls[0].toLocalFile())
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
            if path.is_dir():
                self._set_folder(path)
                event.acceptProposedAction()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            current = self.get_folder()
            start_dir = str(current) if current and current.exists() else str(Path.home())
            folder = QFileDialog.getExistingDirectory(
                self,
                f"Select {self._label_text} Folder",
                start_dir,
            )
            if folder:
                self._set_folder(Path(folder))

    def _set_folder(self, path: Path) -> None:
        self._hint_label.hide()
        self._path_label.setText(str(path))
        self._path_label.show()
        self.folder_dropped.emit(path)

    def clear(self) -> None:
        self._path_label.hide()
        self._path_label.setText("")
        self._hint_label.show()

    def get_folder(self) -> Path | None:
        text = self._path_label.text()
        return Path(text) if text else None
