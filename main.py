#!/usr/bin/env python3
"""
Main script to run the Telegram bot for interacting with LLM services.
"""
from pathlib import Path

from src.telegram_utils import (
    ChatSession,
    load_models_info,
    load_yaml,
    send_startup_message,
)

# Base directory and config paths
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"
MODELS_INFO_PATH = BASE_DIR / "config" / "models_info.json"


def main() -> None:
    """Load config, create chat session, and start polling loop."""
    # Load config and models info
    cfg = load_yaml(CONFIG_PATH)
    models_info = load_models_info(MODELS_INFO_PATH)

    # Create chat session
    session = ChatSession(cfg, models_info)

    # Retrieve chat_id from config.yaml
    chat_ids = cfg.get("telegram", {}).get("chat_id", [])

    # Check if there is at least one chat_id in the list
    if chat_ids:
        # Send startup message to each chat_id
        for chat_id in chat_ids:
            send_startup_message(
                session.bot_token,
                chat_id,
                session.service,
                session.model,
                session.temperature,
                session.max_tokens,
            )
        print(f"Sent startup message to chat_ids: {chat_ids}")
    else:
        print("[ERROR] chat_id not found in config.yaml.")

    # Start the session polling loop
    session.run()


if __name__ == "__main__":
    main()
