import asyncio

from settings.models import EngineName
from settings.installers.protocol import EngineInstaller
from settings.installers.easyocr import EasyOCRInstaller
from settings.installers.tesseract import TesseractInstaller

_INSTALLERS: dict[EngineName, EngineInstaller] = {
    EngineName.EASYOCR: EasyOCRInstaller(),
    EngineName.TESSERACT: TesseractInstaller(),
}


async def is_engine_available(engine: EngineName) -> bool:
    installer = _INSTALLERS[engine]
    return await installer.is_available()


async def get_engines_status() -> dict[EngineName, bool]:
    results = await asyncio.gather(*[is_engine_available(e) for e in EngineName])
    return dict(zip(EngineName, results))


async def install_engine(engine: EngineName) -> None:
    installer = _INSTALLERS[engine]
    await installer.install()
