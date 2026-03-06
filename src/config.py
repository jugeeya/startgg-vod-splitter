"""Load/save app settings: start.gg API token, last event slug, tournament name."""
import json
import os
import sys

# When running as PyInstaller exe, store config next to the executable
if getattr(sys, "frozen", False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_DIR = os.path.join(_BASE_DIR, "config")
_CONFIG_FILE = os.path.join(_CONFIG_DIR, "settings.json")


def _ensure_config_dir():
    os.makedirs(_CONFIG_DIR, exist_ok=True)


def load_settings():
    """Return dict with 'api_token', 'event_slug', 'tournament_name' (may be empty)."""
    defaults = {"api_token": "", "event_slug": "", "tournament_name": ""}
    if not os.path.isfile(_CONFIG_FILE):
        return defaults
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**defaults, **data}
    except (json.JSONDecodeError, OSError):
        return defaults


def save_settings(api_token: str = None, event_slug: str = None, tournament_name: str = None):
    """Update and persist settings. None means leave existing value."""
    _ensure_config_dir()
    current = load_settings()
    if api_token is not None:
        current["api_token"] = api_token
    if event_slug is not None:
        current["event_slug"] = event_slug
    if tournament_name is not None:
        current["tournament_name"] = tournament_name
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
