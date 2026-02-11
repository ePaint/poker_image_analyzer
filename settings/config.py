from pathlib import Path
import tomllib
import tomli_w

SETTINGS_PATH = Path.cwd() / "settings.toml"
DEFAULT_SETTINGS: dict = {
    "last_screenshots_folder": "",
    "last_hands_folder": "",
    "last_output_folder": "",
    "parallel_api_calls": 5,
    "api_rate_limit_per_minute": 50,
}


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
