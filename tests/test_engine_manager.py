import pytest

from settings.models import EngineName
from settings.engine_manager import (
    is_engine_available,
    get_engines_status,
    install_engine,
)


@pytest.mark.asyncio
async def test_is_engine_available_returns_bool():
    result = await is_engine_available(EngineName.EASYOCR)
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_get_engines_status_returns_all_engines():
    result = await get_engines_status()
    assert isinstance(result, dict)
    for engine in EngineName:
        assert engine in result
        assert isinstance(result[engine], bool)


@pytest.mark.asyncio
async def test_install_engine_raises_on_failure(monkeypatch):
    async def mock_install(self):
        raise RuntimeError("Mock installation failure")

    from settings.installers.easyocr import EasyOCRInstaller
    monkeypatch.setattr(EasyOCRInstaller, "install", mock_install)

    with pytest.raises(RuntimeError, match="Mock installation failure"):
        await install_engine(EngineName.EASYOCR)
