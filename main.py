#!/usr/bin/env python3
"""
Main script to run the Telegram bot for interacting with LLM services.
"""
import signal
import sys
from pathlib import Path

from src.telegram_utils import (
    ChatSession,
    load_json,
    load_yaml,
    send_startup_message,
)

# Paths to configuration files
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"
MODELS_INFO_PATH = BASE_DIR / "config" / "models_info.json"


def main() -> None:
    """Load config, create chat session, and start polling loop."""
    try:
        # Load config and models info
        cfg = load_yaml(CONFIG_PATH)
        models_info = load_json(MODELS_INFO_PATH)

        # Attach source path to config so the session can write to it
        cfg["_source_path"] = str(CONFIG_PATH)

        # Create the bot session
        session = ChatSession(cfg, models_info)

        # Retrieve chat_ids from config
        chat_ids = cfg.get("telegram", {}).get("chat_id", [])
        if not isinstance(chat_ids, list):
            chat_ids = [chat_ids] if chat_ids else []

        # Send a startup message to all allowed chat_ids
        if chat_ids:
            for chat_id in chat_ids:
                send_startup_message(
                    session.bot_token,
                    chat_id,
                    session.service,
                    session.model,
                    session.temperature,
                    session.max_tokens,
                )
            print(f"✅ Sent startup message to chat_ids: {chat_ids}")
        else:
            print("[ERROR] No chat_id(s) defined in config.yaml.")

        # Run the polling loop
        session.run()

    except Exception as e:
        print(f"[FATAL] Startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Gracefully handle Ctrl+C
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    main()
