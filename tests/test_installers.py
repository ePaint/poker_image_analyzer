import pytest
import sys


@pytest.mark.asyncio
async def test_easyocr_is_available_true_when_installed():
    from settings.installers.easyocr import EasyOCRInstaller
    installer = EasyOCRInstaller()
    result = await installer.is_available()
    try:
        import easyocr
        assert result is True
    except ImportError:
        assert result is False


@pytest.mark.asyncio
async def test_easyocr_is_available_false_when_missing(monkeypatch):
    from settings.installers.easyocr import EasyOCRInstaller

    original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

    def mock_import(name, *args, **kwargs):
        if name == "easyocr":
            raise ImportError("Mocked missing easyocr")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", mock_import)
    if "easyocr" in sys.modules:
        monkeypatch.delitem(sys.modules, "easyocr")

    installer = EasyOCRInstaller()
    result = await installer.is_available()
    assert result is False


@pytest.mark.asyncio
async def test_tesseract_is_available_checks_both(monkeypatch):
    from settings.installers.tesseract import TesseractInstaller, BIN_DIR

    original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

    def mock_import(name, *args, **kwargs):
        if name == "pytesseract":
            raise ImportError("Mocked missing pytesseract")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", mock_import)
    if "pytesseract" in sys.modules:
        monkeypatch.delitem(sys.modules, "pytesseract")

    installer = TesseractInstaller()
    result = await installer.is_available()
    assert result is False

    monkeypatch.undo()

    class MockPath:
        def exists(self):
            return False

    monkeypatch.setattr("settings.installers.tesseract.BIN_DIR", MockPath())

    installer = TesseractInstaller()
    result = await installer.is_available()
    assert result is False
