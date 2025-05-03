import json
import os
from typing import Any

import yaml
from pydantic import ValidationError

from llm_telegram_bot.config.schemas import RootConfig
from llm_telegram_bot.utils.logger import logger

# Constants
CONFIG_YAML = "config/config.yaml"
MODELS_INFO_JSON = "config/models_info.json"


def load_model_info(json_path: str = MODELS_INFO_JSON) -> dict[str, Any]:
    """
    Load model metadata from a JSON file, returning an empty dict on any error.
    """
    if not os.path.exists(json_path):
        logger.warning(f"[Config Loader] Model info file not found, continuing without it: {json_path}")
        return {}

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[Config Loader] Failed to load model info JSON: {e}")
        return {}


def load_config(config_path: str = CONFIG_YAML) -> RootConfig:
    """
    Load, merge, and validate the full configuration via Pydantic RootConfig.
    Raises ValidationError if any field is missing or mistyped.
    """
    if not os.path.exists(config_path):
        logger.error(f"[Config Loader] Config file not found: {config_path}")
        raise FileNotFoundError(config_path)

    logger.info(f"[Config Loader] Loading config from: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    # Merge in model-info JSON
    raw["models_info"] = load_model_info()

    try:
        cfg = RootConfig.model_validate(raw)
    except ValidationError as e:
        logger.error("[Config Loader] Configuration validation failed:\n" + e.json())
        raise

    logger.info("[Config Loader] Configuration loaded and validated successfully.")
    return cfg
