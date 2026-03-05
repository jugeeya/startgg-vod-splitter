"""Load/save app settings: start.gg API token, last event slug."""
import json
import os

# Use app dir next to the script so it works when run from anywhere
_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
_CONFIG_FILE = os.path.join(_CONFIG_DIR, "settings.json")


def _ensure_config_dir():
    os.makedirs(_CONFIG_DIR, exist_ok=True)


def load_settings():
    """Return dict with 'api_token' and 'event_slug' (may be empty)."""
    defaults = {"api_token": "", "event_slug": ""}
    if not os.path.isfile(_CONFIG_FILE):
        return defaults
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**defaults, **data}
    except (json.JSONDecodeError, OSError):
        return defaults


def save_settings(api_token: str = None, event_slug: str = None):
    """Update and persist settings. None means leave existing value."""
    _ensure_config_dir()
    current = load_settings()
    if api_token is not None:
        current["api_token"] = api_token
    if event_slug is not None:
        current["event_slug"] = event_slug
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
