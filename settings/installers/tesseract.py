import asyncio
import subprocess
from pathlib import Path

TESSERACT_RELEASE_URL = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.5.0.20241111/tesseract-ocr-w64-setup-5.5.0.20241111.exe"
BIN_DIR = Path(__file__).parent.parent.parent / "image_analyzer" / "bin" / "tesseract"
TEMP_DIR = Path(__file__).parent.parent.parent / "temp"


class TesseractInstaller:
    async def is_available(self) -> bool:
        try:
            import pytesseract
        except ImportError:
            return False
        tesseract_exe = BIN_DIR / "tesseract.exe"
        return tesseract_exe.exists()

    async def install(self) -> None:
        await self._install_python_package()
        await self._install_binary()
        self._configure_pytesseract()

    async def _install_python_package(self) -> None:
        process = await asyncio.create_subprocess_exec(
            "uv", "add", "pytesseract",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"Failed to install pytesseract: {stderr.decode()}")

    async def _install_binary(self) -> None:
        TEMP_DIR.mkdir(exist_ok=True)
        BIN_DIR.mkdir(parents=True, exist_ok=True)

        installer_path = TEMP_DIR / "tesseract-installer.exe"
        await self._download_file(TESSERACT_RELEASE_URL, installer_path)

        process = await asyncio.create_subprocess_exec(
            str(installer_path),
            "/S",
            f"/D={BIN_DIR}",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        await process.communicate()
        if process.returncode != 0:
            raise RuntimeError("Tesseract installer failed")

    async def _download_file(self, url: str, dest: Path) -> None:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise RuntimeError(f"Download failed: {response.status}")
                dest.write_bytes(await response.read())

    def _configure_pytesseract(self) -> None:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = str(BIN_DIR / "tesseract.exe")
