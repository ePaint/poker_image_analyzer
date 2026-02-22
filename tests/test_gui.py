"""Tests for GUI components using pytest-qt."""
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QLineEdit

from gui.drop_zone import DropZone
from gui.file_list import FileListWidget
from gui.settings_dialog import (
    SettingsDialog,
    load_api_key,
    save_api_key,
    load_seat_mapping,
    save_seat_mapping,
    load_corrections,
    save_corrections,
)
from gui.main_window import MainWindow
from gui.version import get_version, _read_pyproject_version


class TestVersion:
    def test_get_version_returns_string(self):
        version = get_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_get_version_matches_pyproject(self):
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        assert pyproject_path.exists(), "pyproject.toml should exist"

        import tomllib
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        expected_version = data["project"]["version"]

        assert get_version() == expected_version

    def test_read_pyproject_version_returns_version(self):
        version = _read_pyproject_version()
        assert version is not None
        assert isinstance(version, str)
        assert "." in version  # Version should have at least one dot (e.g., "0.1.3")

    def test_get_version_fallback_to_dev(self):
        from importlib.metadata import PackageNotFoundError
        with patch("gui.version._read_pyproject_version", return_value=None):
            with patch("gui.version.version", side_effect=PackageNotFoundError("oitnow2")):
                version = get_version()
                assert version == "dev"


class TestDropZone:
    def test_drop_zone_initial_state(self, qtbot):
        widget = DropZone("Test Label")
        qtbot.addWidget(widget)

        assert widget.get_folder() is None
        assert widget.acceptDrops()

    def test_drop_zone_emits_signal_on_folder_set(self, qtbot, tmp_path):
        widget = DropZone("Screenshots")
        qtbot.addWidget(widget)

        with qtbot.waitSignal(widget.folder_dropped, timeout=1000) as blocker:
            widget._set_folder(tmp_path)

        assert blocker.args == [tmp_path]
        assert widget.get_folder() == tmp_path

    def test_drop_zone_clear(self, qtbot, tmp_path):
        widget = DropZone("Screenshots")
        qtbot.addWidget(widget)

        widget._set_folder(tmp_path)
        assert widget.get_folder() == tmp_path

        widget.clear()
        assert widget.get_folder() is None


class TestFileListWidget:
    def test_file_list_initial_state(self, qtbot):
        widget = FileListWidget("Test Files")
        qtbot.addWidget(widget)

        assert widget.count() == 0
        assert widget.get_files() == []

    def test_file_list_populates_on_set_folder(self, qtbot, tmp_path):
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.txt").touch()
        (tmp_path / "file3.png").touch()

        widget = FileListWidget("Text Files")
        qtbot.addWidget(widget)

        count = widget.set_folder(tmp_path, "*.txt")

        assert count == 2
        assert widget.count() == 2

    def test_file_list_with_validator(self, qtbot, tmp_path):
        (tmp_path / "valid.txt").touch()
        (tmp_path / "invalid.txt").touch()

        def validator(name: str) -> bool:
            return name.startswith("valid")

        widget = FileListWidget("Files", validator=validator)
        qtbot.addWidget(widget)

        valid_count = widget.set_folder(tmp_path, "*.txt")

        assert valid_count == 1
        assert widget.count() == 2
        assert widget.valid_count() == 1
        assert len(widget.get_valid_files()) == 1

    def test_file_list_refresh_signal(self, qtbot):
        widget = FileListWidget("Test")
        qtbot.addWidget(widget)

        with qtbot.waitSignal(widget.refresh_clicked, timeout=1000):
            widget._refresh_btn.click()

    def test_file_list_refresh_rereads_folder(self, qtbot, tmp_path):
        (tmp_path / "file1.txt").touch()

        widget = FileListWidget("Test")
        qtbot.addWidget(widget)
        widget.set_folder(tmp_path, "*.txt")
        assert widget.count() == 1

        (tmp_path / "file2.txt").touch()
        widget.refresh()
        assert widget.count() == 2

    def test_file_list_handles_missing_folder(self, qtbot, tmp_path):
        widget = FileListWidget("Files")
        qtbot.addWidget(widget)

        missing = tmp_path / "nonexistent"
        count = widget.set_folder(missing, "*.txt")

        assert count == 0
        assert widget.count() == 0


class TestSettingsDialog:
    def test_settings_dialog_masks_api_key(self, qtbot):
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        assert dialog._api_key_input.echoMode() == QLineEdit.EchoMode.Password

    def test_settings_dialog_toggles_key_visibility(self, qtbot):
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        assert dialog._api_key_input.echoMode() == QLineEdit.EchoMode.Password

        dialog._show_key_btn.setChecked(True)
        assert dialog._api_key_input.echoMode() == QLineEdit.EchoMode.Normal

        dialog._show_key_btn.setChecked(False)
        assert dialog._api_key_input.echoMode() == QLineEdit.EchoMode.Password

    def test_settings_dialog_get_api_key(self, qtbot):
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        dialog._api_key_input.setText("  test-key-123  ")
        assert dialog.get_api_key() == "test-key-123"

    def test_settings_dialog_seat_spinboxes_exist(self, qtbot):
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Now we have 2 table types
        assert len(dialog._seat_spinboxes) == 2
        assert "6_player" in dialog._seat_spinboxes
        assert "5_player" in dialog._seat_spinboxes
        # 6-player has 6 positions, 5-player has 5
        assert len(dialog._seat_spinboxes["6_player"]) == 6
        assert len(dialog._seat_spinboxes["5_player"]) == 5

    def test_settings_dialog_reset_seat_mapping(self, qtbot):
        from gui.settings_dialog import DEFAULT_SEATS
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # Set all spinboxes to 9
        for table_type, spinboxes in dialog._seat_spinboxes.items():
            for spinbox in spinboxes.values():
                spinbox.setValue(9)

        dialog._reset_seat_mapping()

        # Verify all reset to defaults
        for table_type, spinboxes in dialog._seat_spinboxes.items():
            for position, spinbox in spinboxes.items():
                assert spinbox.value() == DEFAULT_SEATS[table_type][position]

    def test_settings_dialog_add_correction_row(self, qtbot):
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        initial_rows = dialog._corrections_table.rowCount()
        dialog._add_correction_row()

        assert dialog._corrections_table.rowCount() == initial_rows + 1

    def test_settings_dialog_remove_correction_row(self, qtbot):
        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        dialog._add_correction_row()
        dialog._add_correction_row()
        rows_after_add = dialog._corrections_table.rowCount()

        dialog._corrections_table.setCurrentCell(0, 0)
        dialog._remove_correction_row()

        assert dialog._corrections_table.rowCount() == rows_after_add - 1


class TestSettingsFunctions:
    def test_save_and_load_api_key(self, tmp_path):
        env_file = tmp_path / ".env"

        with patch("gui.settings_dialog._get_env_path", return_value=env_file):
            save_api_key("test-api-key-123")
            assert env_file.exists()

            loaded = load_api_key()
            assert loaded == "test-api-key-123"

    def test_load_api_key_from_env_var(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-var-key")

        with patch("gui.settings_dialog._get_env_path", return_value=env_file):
            loaded = load_api_key()
            assert loaded == "env-var-key"

    def test_save_and_load_seat_mapping(self, tmp_path, monkeypatch):
        mapping_file = tmp_path / "seat_mapping.toml"

        with patch("gui.settings_dialog._get_user_seat_mapping_path", return_value=mapping_file):
            test_mapping = {
                "6_player": {"bottom": 3, "top": 1},
                "5_player": {"bottom": 2, "left": 5},
            }
            save_seat_mapping(test_mapping)

            loaded = load_seat_mapping()
            assert loaded["6_player"]["bottom"] == 3
            assert loaded["6_player"]["top"] == 1
            assert loaded["5_player"]["bottom"] == 2
            assert loaded["5_player"]["left"] == 5

    def test_save_and_load_corrections(self, tmp_path):
        corrections_file = tmp_path / "corrections.toml"

        with patch("gui.settings_dialog._get_user_corrections_path", return_value=corrections_file):
            test_corrections = {"WRONG": "RIGHT", "BAD": "GOOD"}
            save_corrections(test_corrections)

            loaded = load_corrections()
            assert loaded["WRONG"] == "RIGHT"
            assert loaded["BAD"] == "GOOD"


class TestMainWindow:
    def test_main_window_initial_state(self, qtbot, monkeypatch):
        monkeypatch.setattr("gui.main_window.load_settings", lambda: {})
        window = MainWindow()
        qtbot.addWidget(window)

        assert not window._convert_btn.isEnabled()
        assert not window._cancel_btn.isEnabled()

    def test_convert_button_disabled_without_inputs(self, qtbot, monkeypatch):
        monkeypatch.setattr("gui.main_window.load_settings", lambda: {})
        window = MainWindow()
        qtbot.addWidget(window)

        assert not window._convert_btn.isEnabled()

    def test_convert_button_enabled_with_valid_inputs(self, qtbot, tmp_path, monkeypatch):
        monkeypatch.setattr("gui.main_window.load_settings", lambda: {})
        monkeypatch.setattr("gui.main_window.save_settings", lambda x: None)
        screenshots_dir = tmp_path / "screenshots"
        screenshots_dir.mkdir()
        (screenshots_dir / "2024-02-08_ 10-30_AM_$0.01_$0.02_#12345.png").touch()

        hands_dir = tmp_path / "hands"
        hands_dir.mkdir()
        (hands_dir / "hand1.txt").touch()

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        window = MainWindow()
        qtbot.addWidget(window)

        window._on_screenshots_folder_changed(screenshots_dir)
        window._on_hands_folder_changed(hands_dir)
        window._output_input.setText(str(output_dir))
        window._on_output_changed(str(output_dir))

        assert window._convert_btn.isEnabled()
