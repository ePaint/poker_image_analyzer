import pytest
import tomli_w
from settings import load_settings, save_settings, get_engine
from settings.config import DEFAULT_SETTINGS, SETTINGS_PATH
from image_analyzer.engines.easyocr_engine import EasyOCREngine


class TestLoadSettings:
    def test_returns_dict(self):
        result = load_settings()
        assert isinstance(result, dict)

    def test_has_ocr_section(self):
        result = load_settings()
        assert "ocr" in result

    def test_default_engine_is_easyocr(self):
        result = load_settings()
        assert result["ocr"]["engine"] == "easyocr"

    def test_default_gpu_is_false(self):
        result = load_settings()
        assert result["ocr"]["gpu"] is False

    def test_returns_defaults_when_file_missing(self, tmp_path, monkeypatch):
        nonexistent = tmp_path / "nonexistent.toml"
        monkeypatch.setattr("settings.config.SETTINGS_PATH", nonexistent)
        result = load_settings()
        assert result == DEFAULT_SETTINGS

    def test_loads_custom_values_from_file(self, tmp_path, monkeypatch):
        test_path = tmp_path / "settings.toml"
        monkeypatch.setattr("settings.config.SETTINGS_PATH", test_path)
        custom = {"ocr": {"engine": "tesseract", "gpu": True}}
        with open(test_path, "wb") as f:
            tomli_w.dump(custom, f)
        result = load_settings()
        assert result == custom


class TestSaveSettings:
    def test_creates_file(self, tmp_path, monkeypatch):
        test_path = tmp_path / "settings.toml"
        monkeypatch.setattr("settings.config.SETTINGS_PATH", test_path)
        assert not test_path.exists()
        save_settings({"ocr": {"engine": "easyocr", "gpu": False}})
        assert test_path.exists()

    def test_overwrites_existing_file(self, tmp_path, monkeypatch):
        test_path = tmp_path / "settings.toml"
        monkeypatch.setattr("settings.config.SETTINGS_PATH", test_path)
        save_settings({"ocr": {"engine": "easyocr", "gpu": False}})
        save_settings({"ocr": {"engine": "tesseract", "gpu": True}})
        result = load_settings()
        assert result["ocr"]["engine"] == "tesseract"
        assert result["ocr"]["gpu"] is True

    def test_roundtrip_preserves_data(self, tmp_path, monkeypatch):
        test_path = tmp_path / "settings.toml"
        monkeypatch.setattr("settings.config.SETTINGS_PATH", test_path)
        original = {"ocr": {"engine": "tesseract", "gpu": True}, "other": {"key": "value"}}
        save_settings(original)
        loaded = load_settings()
        assert loaded == original


class TestGetEngine:
    def test_returns_easyocr_by_default(self):
        engine = get_engine()
        assert isinstance(engine, EasyOCREngine)

    def test_raises_on_unknown_engine(self, tmp_path, monkeypatch):
        test_path = tmp_path / "settings.toml"
        monkeypatch.setattr("settings.config.SETTINGS_PATH", test_path)
        with open(test_path, "wb") as f:
            tomli_w.dump({"ocr": {"engine": "unknown"}}, f)
        with pytest.raises(ValueError, match="Unknown OCR engine"):
            get_engine()

    def test_uses_defaults_when_ocr_section_missing(self, tmp_path, monkeypatch):
        test_path = tmp_path / "settings.toml"
        monkeypatch.setattr("settings.config.SETTINGS_PATH", test_path)
        with open(test_path, "wb") as f:
            tomli_w.dump({}, f)
        engine = get_engine()
        assert isinstance(engine, EasyOCREngine)

    def test_uses_default_engine_when_key_missing(self, tmp_path, monkeypatch):
        test_path = tmp_path / "settings.toml"
        monkeypatch.setattr("settings.config.SETTINGS_PATH", test_path)
        with open(test_path, "wb") as f:
            tomli_w.dump({"ocr": {"gpu": True}}, f)
        engine = get_engine()
        assert isinstance(engine, EasyOCREngine)


class TestDefaultSettings:
    def test_default_settings_structure(self):
        assert "ocr" in DEFAULT_SETTINGS
        assert "engine" in DEFAULT_SETTINGS["ocr"]
        assert "gpu" in DEFAULT_SETTINGS["ocr"]

    def test_default_settings_values(self):
        assert DEFAULT_SETTINGS["ocr"]["engine"] == "easyocr"
        assert DEFAULT_SETTINGS["ocr"]["gpu"] is False
