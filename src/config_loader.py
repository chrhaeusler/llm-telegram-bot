# src/config_loader.py

import logging
import os
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Optional: also print to console for dev use
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
logger.addHandler(console_handler)


def load_yaml_file(path: str) -> Dict[str, Any]:
    """Loads a YAML file and returns its contents as a dictionary."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    logger.debug(f"Loaded config from {path}: {data}")
    return data


def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merges two dictionaries, with override taking precedence."""
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = merge_configs(base[k], v)
        else:
            base[k] = v
    return base


def load_combined_config(
    main_path="config/config.yaml",
    cli_path="config/chatbot.yaml",
) -> Dict[str, Any]:
    """Loads and combines main, CLI-specific, and credentials config files."""
    logger.info("Loading configuration...")
    main_config = load_yaml_file(main_path)
    cli_config = load_yaml_file(cli_path)

    final_config = merge_configs(main_config, cli_config)

    logger.info("Final merged config:")
    logger.debug(final_config)
    return final_config


if __name__ == "__main__":
    cfg = load_combined_config()
    print("Loaded config:\n", cfg)
