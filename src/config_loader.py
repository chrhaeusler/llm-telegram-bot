import logging
import os
from typing import Any, Dict

import yaml

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Optional: also print to console for dev use
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
logger.addHandler(console_handler)


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """
    Loads and validates the unified configuration from a YAML file.

    Args:
        config_path: Path to the config YAML file.

    Returns:
        A dictionary containing the parsed config.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        ValueError: If required fields are missing.
    """
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        raise FileNotFoundError(f"Config file not found: {config_path}")

    logger.debug(f"Loading config from: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = yaml.safe_load(f)

    # Validate top-level keys
    required_top_keys = ["telegram", "services"]
    for key in required_top_keys:
        if key not in config:
            logger.error(f"Missing required config section: '{key}'")
            raise ValueError(f"Missing required config section: '{key}'")

    # Validate Telegram bot configs
    telegram_config = config["telegram"]
    bots = {k: v for k, v in telegram_config.items() if k.startswith("bot_")}
    if not bots:
        logger.error("No bot configuration found under 'telegram'")
        raise ValueError("No bot configuration found under 'telegram'")

    for bot_name, bot_conf in bots.items():
        logger.debug(f"Validating bot: {bot_name}")
        for required_field in ["token", "chat_id", "default"]:
            if required_field not in bot_conf:
                logger.error(f"Missing '{required_field}' for {bot_name}")
                raise ValueError(f"Missing '{required_field}' for {bot_name}")
        for field in ["service", "model", "temperature", "maxtoken"]:
            if field not in bot_conf["default"]:
                logger.error(f"Missing default.{field} in {bot_name}")
                raise ValueError(f"Missing default.{field} in {bot_name}")

    # Validate global polling settings
    if "polling_interval_active" not in telegram_config:
        logger.error("Missing 'polling_interval_active' in telegram config")
        raise ValueError("Missing 'polling_interval_active' in telegram config")
    if "polling_interval_idle" not in telegram_config:
        logger.error("Missing 'polling_interval_idle' in telegram config")
        raise ValueError("Missing 'polling_interval_idle' in telegram config")

    logger.debug("Configuration loaded and validated successfully.")
    return config
