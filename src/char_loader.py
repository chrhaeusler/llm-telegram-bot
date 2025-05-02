import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class Character:
    key: str
    role: str
    description: str
    identity: Dict[str, Any]
    system: Dict[str, Any]
    instructions: List[str]
    memory_buckets: Dict[str, List[Any]]
    roleplay_guidelines: Optional[str] = None


# Directory where character YAML files live
_CHAR_DIR = Path("config/chars")


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load char file {path.name}: {e}")
        return {}


def get_all_characters() -> Dict[str, dict]:
    """
    Load and parse all character YAML files under config/chars.
    Returns a mapping of key -> dict.
    """
    chars: Dict[str, dict] = {}
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
        except Exception as e:
            logger.error(f"Error parsing char file {file.name}: {e}")
    return chars


def get_character(key: str) -> Optional[dict]:
    """Retrieve a single character config dict by key, or None if not found."""
    return get_all_characters().get(key)
