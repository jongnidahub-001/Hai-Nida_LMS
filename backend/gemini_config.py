"""
Gemini configuration - read/write model selection and API key from config file.
Supports multi-model configuration per role (planner, writer, grader).
Backward compatible with legacy single-model format.
"""
import os
import json
from pathlib import Path
from typing import Literal

CONFIG_DIR = Path(__file__).resolve().parent / "config"
CONFIG_FILE = CONFIG_DIR / "gemini_settings.json"
DEFAULT_MODEL = "gemini-2.5-flash-lite"

# Default models per role
DEFAULT_MODELS = {
    "planner": "gemini-2.5-flash-lite",
    "writer": "gemini-2.5-flash-lite",
    "grader": "gemini-2.5-flash-lite",
}

# Valid role names
VALID_ROLES = ("planner", "writer", "grader")

RoleType = Literal["planner", "writer", "grader"]


def _ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _read_config() -> dict:
    """Read the entire config file. Returns empty dict on failure."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _write_config(data: dict) -> None:
    """Write config data to config file (merges with existing)."""
    _ensure_config_dir()
    existing = _read_config()
    existing.update(data)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


# ============== Legacy single-model API (backward compatible) ==============

def get_gemini_model() -> str:
    """Get the currently selected Gemini model. Returns default if not set.
    Legacy API - returns writer model for backward compatibility."""
    data = _read_config()
    # New format: use writer_model
    if "writer_model" in data:
        return data["writer_model"]
    # Legacy format: use model
    return data.get("model") or DEFAULT_MODEL


def set_gemini_model(model: str) -> None:
    """Save the selected Gemini model to config file.
    Legacy API - sets all roles to the same model for backward compatibility."""
    _write_config({
        "model": model,
        "planner_model": model,
        "writer_model": model,
        "grader_model": model,
    })


# ============== Multi-model API (per role) ==============

def get_model_for_role(role: RoleType) -> str:
    """Get the model configured for a specific role.
    
    Args:
        role: One of 'planner', 'writer', 'grader'
        
    Returns:
        Model name string
    """
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role '{role}'. Must be one of: {VALID_ROLES}")
    
    data = _read_config()
    role_key = f"{role}_model"
    
    # Try role-specific model first
    if role_key in data:
        return data[role_key]
    
    # Fallback to legacy single model
    if "model" in data:
        return data["model"]
    
    # Default
    return DEFAULT_MODELS.get(role, DEFAULT_MODEL)


def set_model_for_role(role: RoleType, model: str) -> None:
    """Save the model for a specific role.
    
    Args:
        role: One of 'planner', 'writer', 'grader'
        model: Model name string (e.g. 'gemini-2.5-pro')
    """
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role '{role}'. Must be one of: {VALID_ROLES}")
    
    role_key = f"{role}_model"
    _write_config({role_key: model})


def get_all_role_models() -> dict:
    """Get all role-model mappings.
    
    Returns:
        dict with keys: planner_model, writer_model, grader_model
    """
    return {
        "planner_model": get_model_for_role("planner"),
        "writer_model": get_model_for_role("writer"),
        "grader_model": get_model_for_role("grader"),
    }


# ============== API Key ==============

def get_gemini_api_key() -> str:
    """Get Gemini API key. Priority: config file > .env GOOGLE_API_KEY."""
    data = _read_config()
    config_key = data.get("api_key")
    if config_key:
        return config_key
    return os.environ.get("GOOGLE_API_KEY", "")


def set_gemini_api_key(api_key: str) -> None:
    """Save the Gemini API key to config file."""
    _write_config({"api_key": api_key})
