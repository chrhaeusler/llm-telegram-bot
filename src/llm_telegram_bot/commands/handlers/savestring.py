# src/commands/handlers/savestring.py

import os
import time
from pathlib import Path
from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.config.schemas import BotConfig
from llm_telegram_bot.utils.logger import logger

# Log that the save string handler is being loaded
logger.info("[Savestring Handler] savestring.py is being loaded")


@register_command("/sstr")
async def savestring_handler(session: Any, message: dict[str, Any], args: List[str]) -> None:
    """
    /sstr [<filename>] <text>
    • If filename ends in .txt/.log/.md → use it
    • Otherwise auto-generate one using timestamp
    Saves into: <download_path>/<bot_name>/<chat_id>/<filename>
    """
    raw = message.get("text", "").strip().split()[1:]  # remove command itself
    if not raw:
        await session.send_message("⚠️ Usage: /sstr [filename] <text>")
        return

    ts = time.strftime("%Y-%m-%d_%H-%M-%S")
    # Check if first word looks like a filename
    if len(raw) >= 2 and raw[0].endswith((".txt", ".log", ".md")):
        filename = Path(raw[0]).name
        filename = f"{ts}_{filename}"
        text = " ".join(raw[1:])
    else:
        filename = f"{ts}_saved-string.txt"
        text = " ".join(raw)

    # Determine save directory from config
    cfg = load_config()  # RootConfig
    tg_cfg = cfg.telegram  # TelegramConfig
    bot_conf: BotConfig | None = tg_cfg.bots.get(session.client.bot_name)
    if not bot_conf:
        await session.send_message("❌ Bot configuration not found.")
        return

    # Use bot-level download_path, or fallback to global
    download_root = bot_conf.download_path or tg_cfg.download_path
    full_dir = os.path.join(download_root, bot_conf.name, str(session.chat_id))
    os.makedirs(full_dir, exist_ok=True)

    # Ensure destination filename is unique
    base, ext = os.path.splitext(filename)
    path = os.path.join(full_dir, filename)
    counter = 1
    while os.path.exists(path):
        path = os.path.join(full_dir, f"{base}_{counter}{ext}")
        counter += 1

    # Save the text to file
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        logger.info(f"[savestring] Saved to {path}")
        await session.send_message(f"✅ Saved to `{os.path.basename(path)}`")
    except Exception as e:
        logger.exception("[savestring] Failed to save string")
        await session.send_message(f"❌ Failed to save: {e}")
