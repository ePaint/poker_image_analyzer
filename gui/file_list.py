"""File list widget for previewing files in a folder."""
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
)


class FileListWidget(QWidget):
    """A widget showing a list of files with optional validation."""

    refresh_clicked = Signal()

    def __init__(
        self,
        title: str,
        validator: Callable[[str], bool] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._title = title
        self._validator = validator
        self._current_folder: Path | None = None
        self._current_pattern: str | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self._header = QLabel(f"{self._title} (0 files)")
        self._header.setStyleSheet("font-weight: bold;")

        self._refresh_btn = QPushButton("⟳")
        self._refresh_btn.setFixedSize(24, 24)
        self._refresh_btn.setToolTip("Refresh file list")
        self._refresh_btn.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        self._refresh_btn.clicked.connect(self.refresh_clicked.emit)

        header_layout.addWidget(self._header)
        header_layout.addWidget(self._refresh_btn)
        header_layout.addStretch()

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.setStyleSheet("""
            QListWidget {
                background-color: #1a1a1a;
                border: 1px solid #444;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:alternate {
                background-color: #222;
            }
        """)

        layout.addLayout(header_layout)
        layout.addWidget(self._list)

    def set_folder(self, path: Path, pattern: str) -> int:
        """Populate list with files matching pattern.

        Args:
            path: Directory to scan
            pattern: Glob pattern (e.g., "*.png")

        Returns:
            Count of valid files
        """
        self._current_folder = path
        self._current_pattern = pattern
        self._list.clear()

        if not path.exists():
            self._header.setText(f"{self._title} (folder not found)")
            return 0

        files = sorted(path.glob(pattern))
        valid_count = 0

        for file_path in files:
            item = QListWidgetItem(file_path.name)

            is_valid = True
            if self._validator:
                is_valid = self._validator(file_path.name)

            if is_valid:
                valid_count += 1
            else:
                item.setForeground(QColor("#666"))
                item.setToolTip("Invalid file format")

            item.setData(Qt.ItemDataRole.UserRole, str(file_path))
            self._list.addItem(item)

        total = len(files)
        if self._validator and valid_count != total:
            self._header.setText(f"{self._title} ({valid_count}/{total} valid)")
        else:
            self._header.setText(f"{self._title} ({total} files)")

        return valid_count

    def clear(self) -> None:
        self._list.clear()
        self._header.setText(f"{self._title} (0 files)")

    def get_files(self) -> list[Path]:
        """Get list of all file paths (including invalid ones)."""
        files = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            path_str = item.data(Qt.ItemDataRole.UserRole)
            if path_str:
                files.append(Path(path_str))
        return files

    def get_valid_files(self) -> list[Path]:
        """Get list of valid file paths only."""
        if not self._validator:
            return self.get_files()

        files = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            path_str = item.data(Qt.ItemDataRole.UserRole)
            if path_str:
                path = Path(path_str)
                if self._validator(path.name):
                    files.append(path)
        return files

    def count(self) -> int:
        return self._list.count()

    def valid_count(self) -> int:
        if not self._validator:
            return self.count()
        return len(self.get_valid_files())

    def refresh(self) -> int:
        """Re-read current folder if set.

        Returns:
            Count of valid files, or 0 if no folder set
        """
        if self._current_folder and self._current_pattern:
            return self.set_folder(self._current_folder, self._current_pattern)
        return 0
