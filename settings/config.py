import sys
import tomllib
from pathlib import Path

import tomli_w


def _get_app_data_dir() -> Path:
    """Get the application data directory for storing settings."""
    if sys.platform == "darwin":
        app_dir = Path.home() / "Library" / "Application Support" / "HandHistoryDeanonymizer"
    elif sys.platform == "win32":
        import os
        app_dir = Path(os.environ.get("APPDATA", Path.home())) / "HandHistoryDeanonymizer"
    else:
        app_dir = Path.home() / ".config" / "handhistorydeanonymizer"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def _get_settings_path() -> Path:
    """Get the path to settings.toml, preferring local file for development."""
    local_path = Path.cwd() / "settings.toml"
    if local_path.exists():
        return local_path
    return _get_app_data_dir() / "settings.toml"


DEFAULT_SETTINGS: dict = {
    "last_screenshots_folder": "",
    "last_hands_folder": "",
    "last_output_folder": "",
    "parallel_api_calls": 5,
    "api_rate_limit_per_minute": 50,
}


def load_settings() -> dict:
    """Load settings from settings.toml, return defaults if not found."""
    settings_path = _get_settings_path()
    if settings_path.exists():
        with open(settings_path, "rb") as f:
            return tomllib.load(f)
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> None:
    """Save settings to settings.toml in app data directory."""
    settings_path = _get_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_path, "wb") as f:
        tomli_w.dump(settings, f)
