import pytest
import tomli_w
from settings import load_settings, save_settings
from settings.config import DEFAULT_SETTINGS, SETTINGS_PATH


class TestLoadSettings:
    def test_returns_dict(self):
        result = load_settings()
        assert isinstance(result, dict)

    def test_returns_defaults_when_file_missing(self, tmp_path, monkeypatch):
        nonexistent = tmp_path / "nonexistent.toml"
        monkeypatch.setattr("settings.config.SETTINGS_PATH", nonexistent)
        result = load_settings()
        assert result == DEFAULT_SETTINGS

    def test_loads_custom_values_from_file(self, tmp_path, monkeypatch):
        test_path = tmp_path / "settings.toml"
        monkeypatch.setattr("settings.config.SETTINGS_PATH", test_path)
        custom = {"custom_key": "custom_value"}
        with open(test_path, "wb") as f:
            tomli_w.dump(custom, f)
        result = load_settings()
        assert result == custom


class TestSaveSettings:
    def test_creates_file(self, tmp_path, monkeypatch):
        test_path = tmp_path / "settings.toml"
        monkeypatch.setattr("settings.config.SETTINGS_PATH", test_path)
        assert not test_path.exists()
        save_settings({"key": "value"})
        assert test_path.exists()

    def test_overwrites_existing_file(self, tmp_path, monkeypatch):
        test_path = tmp_path / "settings.toml"
        monkeypatch.setattr("settings.config.SETTINGS_PATH", test_path)
        save_settings({"key": "value1"})
        save_settings({"key": "value2"})
        result = load_settings()
        assert result["key"] == "value2"

    def test_roundtrip_preserves_data(self, tmp_path, monkeypatch):
        test_path = tmp_path / "settings.toml"
        monkeypatch.setattr("settings.config.SETTINGS_PATH", test_path)
        original = {"section": {"key": "value"}, "other": {"nested": {"deep": True}}}
        save_settings(original)
        loaded = load_settings()
        assert loaded == original


class TestDefaultSettings:
    def test_default_settings_has_folder_keys(self):
        assert "last_screenshots_folder" in DEFAULT_SETTINGS
        assert "last_hands_folder" in DEFAULT_SETTINGS
        assert "last_output_folder" in DEFAULT_SETTINGS
