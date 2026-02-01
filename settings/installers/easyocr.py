import asyncio
import subprocess


class EasyOCRInstaller:
    async def is_available(self) -> bool:
        try:
            import easyocr
            return True
        except ImportError:
            return False

    async def install(self) -> None:
        process = await asyncio.create_subprocess_exec(
            "uv", "add", "easyocr",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"Failed to install easyocr: {stderr.decode()}")
