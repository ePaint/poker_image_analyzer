from pathlib import Path
import tomllib
import tomli_w

SETTINGS_PATH = Path.cwd() / "settings.toml"
DEFAULT_SETTINGS: dict = {}


def load_settings() -> dict:
    """Load settings.toml from project root, return defaults if not found."""
    if SETTINGS_PATH.exists():
        with open(SETTINGS_PATH, "rb") as f:
            return tomllib.load(f)
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> None:
    """Save settings to settings.toml."""
    with open(SETTINGS_PATH, "wb") as f:
        tomli_w.dump(settings, f)
