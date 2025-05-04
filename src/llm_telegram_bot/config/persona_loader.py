import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Optional

import yaml
from jinja2 import Template

logger = logging.getLogger(__name__)

_CHAR_DIR = Path("config/chars")
_USER_DIR = Path("config/users")

_char_cache: Dict[str, Dict[str, Any]] = {}
_user_cache: Dict[str, Dict[str, Any]] = {}


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)  # Returning Any from function declared to return "dict[str, Any]"
    except Exception as e:
        logger.error(f"Failed to load YAML file {path.name}: {e}")
        return {}


def _render_templates(data: Any, context: Dict[str, Any]) -> Any:
    """Recursively render Jinja-style templates in dicts/lists."""
    if isinstance(data, dict):
        return {k: _render_templates(v, context) for k, v in data.items()}
    elif isinstance(data, list):
        return [_render_templates(item, context) for item in data]
    elif isinstance(data, str):
        try:
            return Template(data).render(**context)
        except Exception as e:
            logger.warning(f"Template render error: {e} in '{data}'")
            return data
    else:
        logger.debug(f"Rendering string: {data} with context keys: {list(context.keys())}")
        return data


# ─── CHARACTERS ─────────────────────────────────────────────────────────────


def get_all_characters() -> Dict[str, Dict[str, Any]]:
    chars: Dict[str, dict] = {}  # Missing type parameters for generic type "dict"
    if not _CHAR_DIR.exists():
        logger.warning(f"Character directory not found: {_CHAR_DIR}")
        return chars

    for file in _CHAR_DIR.glob("*.yaml"):
        data = _load_yaml(file)
        if not data:
            continue
        try:
            key = data["key"]
            chars[key] = data
        except KeyError as e:
            logger.error(f"Missing required field {e} in char file {file.name}")
    return chars


def get_character(char_key: str) -> Optional[Dict[str, Any]]:
    if char_key in _char_cache:
        return _char_cache[char_key]

    path = _CHAR_DIR / f"{char_key}.yaml"
    if not path.exists():
        logger.warning(f"Character file not found: {path}")
        return None

    data = _load_yaml(path)
    if data:
        _char_cache[char_key] = data
    return data


def load_char_config(char_key: Optional[str], user_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    if not char_key:
        return None

    char = get_character(char_key)  # Name "get_character" is not defined

    if not char:
        logger.warning(f"Character '{char_key}' not found.")
        return None

    context = {
        "char": char,
        "user": user_data or {},
        "char_ns": SimpleNamespace(**char),  # Name "SimpleNamespace" is not defined
        "user_ns": SimpleNamespace(**(user_data or {})),
    }  # Name "SimpleNamespace" is not defined

    rendered = _render_templates(char, context)

    return rendered  # Returning Any from function declared to return "dict[Any, Any] | None"


# ─── USERS ───────────────────────────────────────────────────────────────────


def get_all_users() -> Dict[str, Dict[str, Any]]:
    users: Dict[str, dict] = {}  # Missing type parameters for generic type "dict"
    if not _USER_DIR.exists():
        logger.warning(f"User directory not found: {_USER_DIR}")
        return users

    for file in _USER_DIR.glob("*.yaml"):
        data = _load_yaml(file)
        if not data:
            continue
        try:
            key = data["key"]
            users[key] = data
        except KeyError as e:
            logger.error(f"Missing required field {e} in user file {file.name}")
    return users


def get_user(user_key: str) -> Optional[Dict[str, Any]]:
    if user_key in _user_cache:
        return _user_cache[user_key]

    path = _USER_DIR / f"{user_key}.yaml"
    if not path.exists():
        logger.warning(f"User file not found: {path}")
        return None

    data = _load_yaml(path)
    if data:
        _user_cache[user_key] = data
    return data


def load_user_config(user_key: Optional[str], char_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    if not user_key:
        return None

    user = get_user(user_key)  # Name "get_user" is not defined

    if not user:
        logger.warning(f"User '{user_key}' not found.")
        return None

    context = {
        "char": char_data or {},
        "user": user,
        "char_ns": SimpleNamespace(**(char_data or {})),  # Name "SimpleNamespace" is not defined
        "user_ns": SimpleNamespace(**user),
    }  # Name "SimpleNamespace" is not defined

    rendered = _render_templates(user, context)

    return rendered  # Returning Any from function declared to return "dict[Any, Any] | None"
