"""Settings dialog with tabs for API key, seat mapping, and corrections."""
import os
import tomllib
from pathlib import Path

import tomli_w
from dotenv import set_key, dotenv_values

from hand_history import TableType
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QFormLayout,
    QMessageBox,
    QHeaderView,
)


def _get_env_path() -> Path:
    """Get .env path, preferring local for development, else app data dir."""
    local_path = Path.cwd() / ".env"
    if local_path.exists():
        return local_path
    from settings.config import _get_app_data_dir
    return _get_app_data_dir() / ".env"


def _get_seat_mapping_path() -> Path:
    return Path(__file__).parent.parent / "hand_history" / "seat_mapping.toml"


def _get_corrections_path() -> Path:
    return Path(__file__).parent.parent / "image_analyzer" / "corrections.toml"


def load_api_key() -> str | None:
    """Load API key from .env file."""
    env_path = _get_env_path()
    if not env_path.exists():
        return os.environ.get("ANTHROPIC_API_KEY")
    values = dotenv_values(env_path)
    return values.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")


def save_api_key(key: str) -> None:
    """Save API key to .env file."""
    env_path = _get_env_path()
    if not env_path.exists():
        env_path.touch()
    set_key(str(env_path), "ANTHROPIC_API_KEY", key)


DEFAULT_SEATS = {
    "6_player": {
        "bottom": 1,
        "bottom_left": 2,
        "top_left": 3,
        "top": 4,
        "top_right": 5,
        "bottom_right": 6,
    },
    "5_player": {
        "bottom": 1,
        "left": 2,
        "top_left": 3,
        "top_right": 5,
        "right": 6,
    },
}


def load_seat_mapping() -> dict[str, dict[str, int]]:
    """Load seat mappings for all table types."""
    path = _get_seat_mapping_path()
    if not path.exists():
        return {k: v.copy() for k, v in DEFAULT_SEATS.items()}
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return {
        "6_player": data.get("6_player", DEFAULT_SEATS["6_player"].copy()),
        "5_player": data.get("5_player", DEFAULT_SEATS["5_player"].copy()),
    }


def save_seat_mapping(mappings: dict[str, dict[str, int]]) -> None:
    """Save seat mappings to TOML file."""
    path = _get_seat_mapping_path()
    with open(path, "wb") as f:
        tomli_w.dump(mappings, f)


def load_corrections() -> dict[str, str]:
    """Load corrections from TOML file."""
    path = _get_corrections_path()
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data.get("corrections", {})


def save_corrections(corrections: dict[str, str]) -> None:
    """Save corrections to TOML file."""
    path = _get_corrections_path()
    data = {"corrections": corrections}
    with open(path, "wb") as f:
        tomli_w.dump(data, f)


class SettingsDialog(QDialog):
    """Settings dialog with tabs for API key, seat mapping, and corrections."""

    SIX_PLAYER_POSITIONS = ["bottom", "bottom_left", "top_left", "top", "top_right", "bottom_right"]
    FIVE_PLAYER_POSITIONS = ["bottom", "left", "top_left", "top_right", "right"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(450)
        self._setup_ui()
        self._load_values()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._create_api_tab(), "API Key")
        self._tabs.addTab(self._create_seat_mapping_tab(), "Seat Mapping")
        self._tabs.addTab(self._create_corrections_tab(), "Corrections")

        layout.addWidget(self._tabs)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self._save_btn = QPushButton("Save")
        self._save_btn.clicked.connect(self._save)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(self._save_btn)
        button_layout.addWidget(self._cancel_btn)

        layout.addLayout(button_layout)

    def _create_api_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        form = QFormLayout()

        self._api_key_input = QLineEdit()
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.setPlaceholderText("sk-ant-api03-...")

        self._show_key_btn = QPushButton("Show")
        self._show_key_btn.setCheckable(True)
        self._show_key_btn.toggled.connect(self._toggle_key_visibility)

        key_layout = QHBoxLayout()
        key_layout.addWidget(self._api_key_input)
        key_layout.addWidget(self._show_key_btn)

        form.addRow("Anthropic API Key:", key_layout)

        layout.addLayout(form)

        self._test_btn = QPushButton("Test Connection")
        self._test_btn.clicked.connect(self._test_connection)
        layout.addWidget(self._test_btn)

        parallel_layout = QHBoxLayout()
        self._parallel_slider = QSlider(Qt.Orientation.Horizontal)
        self._parallel_slider.setRange(1, 8)
        self._parallel_slider.setValue(5)
        self._parallel_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._parallel_slider.setTickInterval(1)
        self._parallel_slider.setToolTip("Number of screenshots to process simultaneously")
        self._parallel_label = QLabel("5")
        self._parallel_label.setMinimumWidth(25)
        self._parallel_slider.valueChanged.connect(
            lambda v: self._parallel_label.setText(str(v))
        )
        parallel_layout.addWidget(QLabel("Parallel API calls:"))
        parallel_layout.addWidget(self._parallel_slider)
        parallel_layout.addWidget(self._parallel_label)
        layout.addLayout(parallel_layout)

        layout.addStretch()

        return widget

    def _create_seat_mapping_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info_label = QLabel("Map screenshot positions to hand history seat numbers:")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Initialize nested dict for spinboxes
        self._seat_spinboxes: dict[str, dict[str, QSpinBox]] = {}

        # Sub-tabs for each table type
        self._seat_tabs = QTabWidget()
        self._seat_tabs.addTab(
            self._create_seat_form("6_player", self.SIX_PLAYER_POSITIONS),
            "6-player"
        )
        self._seat_tabs.addTab(
            self._create_seat_form("5_player", self.FIVE_PLAYER_POSITIONS),
            "5-player"
        )
        layout.addWidget(self._seat_tabs)

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_seat_mapping)
        layout.addWidget(reset_btn)

        layout.addStretch()

        return widget

    def _create_seat_form(self, table_type: TableType, positions: list[str]) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self._seat_spinboxes[table_type] = {}
        for position in positions:
            spinbox = QSpinBox()
            spinbox.setRange(1, 6)
            spinbox.setValue(DEFAULT_SEATS[table_type][position])
            self._seat_spinboxes[table_type][position] = spinbox
            form.addRow(f"{position}:", spinbox)

        return widget

    def _create_corrections_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info_label = QLabel("Add corrections for recurring OCR errors:")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        self._corrections_table = QTableWidget(0, 2)
        self._corrections_table.setHorizontalHeaderLabels(["Misread", "Correct"])
        self._corrections_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self._corrections_table)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ Add")
        add_btn.clicked.connect(self._add_correction_row)
        remove_btn = QPushButton("- Remove")
        remove_btn.clicked.connect(self._remove_correction_row)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return widget

    def _load_values(self) -> None:
        from settings import load_settings
        settings = load_settings()
        parallel = settings.get("parallel_api_calls", 5)
        self._parallel_slider.setValue(parallel)
        self._parallel_label.setText(str(parallel))

        api_key = load_api_key()
        if api_key:
            self._api_key_input.setText(api_key)

        mappings = load_seat_mapping()
        for table_type, spinboxes in self._seat_spinboxes.items():
            for position, spinbox in spinboxes.items():
                default = DEFAULT_SEATS[table_type].get(position, 1)
                spinbox.setValue(mappings.get(table_type, {}).get(position, default))

        corrections = load_corrections()
        self._corrections_table.setRowCount(len(corrections))
        for i, (misread, correct) in enumerate(corrections.items()):
            self._corrections_table.setItem(i, 0, QTableWidgetItem(misread))
            self._corrections_table.setItem(i, 1, QTableWidgetItem(correct))

    def _toggle_key_visibility(self, checked: bool) -> None:
        if checked:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_key_btn.setText("Hide")
        else:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_key_btn.setText("Show")

    def _test_connection(self) -> None:
        api_key = self._api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Error", "Please enter an API key.")
            return

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            QMessageBox.information(self, "Success", "Connection successful!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Connection failed:\n{e}")

    def _reset_seat_mapping(self) -> None:
        for table_type, spinboxes in self._seat_spinboxes.items():
            for position, spinbox in spinboxes.items():
                spinbox.setValue(DEFAULT_SEATS[table_type][position])

    def _add_correction_row(self) -> None:
        row = self._corrections_table.rowCount()
        self._corrections_table.insertRow(row)
        self._corrections_table.setItem(row, 0, QTableWidgetItem(""))
        self._corrections_table.setItem(row, 1, QTableWidgetItem(""))

    def _remove_correction_row(self) -> None:
        current_row = self._corrections_table.currentRow()
        if current_row >= 0:
            self._corrections_table.removeRow(current_row)

    def _save(self) -> None:
        from settings import load_settings, save_settings
        settings = load_settings()
        settings["parallel_api_calls"] = self._parallel_slider.value()
        save_settings(settings)

        api_key = self._api_key_input.text().strip()
        if api_key:
            save_api_key(api_key)

        mappings = {}
        for table_type, spinboxes in self._seat_spinboxes.items():
            mappings[table_type] = {}
            for position, spinbox in spinboxes.items():
                mappings[table_type][position] = spinbox.value()
        save_seat_mapping(mappings)

        corrections = {}
        for row in range(self._corrections_table.rowCount()):
            misread_item = self._corrections_table.item(row, 0)
            correct_item = self._corrections_table.item(row, 1)
            if misread_item and correct_item:
                misread = misread_item.text().strip()
                correct = correct_item.text().strip()
                if misread and correct:
                    corrections[misread] = correct
        save_corrections(corrections)

        self.accept()

    def get_api_key(self) -> str:
        return self._api_key_input.text().strip()
