"""Version helper for displaying app version."""
import sys
import tomllib
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path


def _read_pyproject_version() -> str | None:
    """Read version from pyproject.toml."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).parent.parent

    pyproject_path = base / "pyproject.toml"
    if not pyproject_path.exists():
        return None

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    return data.get("project", {}).get("version")


def get_version() -> str:
    """Get the package version from pyproject.toml, falling back to metadata."""
    pyproject_version = _read_pyproject_version()
    if pyproject_version:
        return pyproject_version

    try:
        return version("oitnow2")
    except PackageNotFoundError:
        return "dev"
