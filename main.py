#!/usr/bin/env python3
"""
Main script to run the Telegram bot for interacting with LLM services.
"""
import sys
from pathlib import Path

# Add the 'src' directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from telegram_utils import ChatSession, load_models_info, load_yaml

# Base directory and config paths
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"
MODELS_INFO_PATH = BASE_DIR / "config" / "models_info.json"


def main() -> None:
    """Load config, create chat session, and start polling loop."""
    cfg = load_yaml(CONFIG_PATH)
    models_info = load_models_info(MODELS_INFO_PATH)
    session = ChatSession(cfg, models_info)
    session.run()


if __name__ == "__main__":
    main()
