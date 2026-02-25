"""
Gemini model configuration - read/write model selection from config file.
"""
import os
import json
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent / "config"
CONFIG_FILE = CONFIG_DIR / "gemini_settings.json"
DEFAULT_MODEL = "gemini-2.5-flash"


def _ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def get_gemini_model() -> str:
    """Get the currently selected Gemini model. Returns default if not set."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                model = data.get("model")
                if model:
                    return model
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_MODEL


def set_gemini_model(model: str) -> None:
    """Save the selected Gemini model to config file."""
    _ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"model": model}, f, indent=2)
