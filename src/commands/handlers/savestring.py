# src/commands/handlers/savestring.py

import logging
import os
import time
from typing import Any, List

from src.commands.commands_registry import register_command
from src.config_loader import config_loader

logger = logging.getLogger(__name__)
logger.info("[SaveString Handler] savestring.py loaded")


@register_command("/savestr")
async def savestring_handler(session: Any, message: dict[str, Any], args: List[str]):
    """
    /savestring [<filename>] <text>
    • If filename given: save text into that file
    • Else: auto-generate timestamp_savestring.txt
    """
    # Reconstruct raw args (in case of spaces)
    raw = message.get("text", "").strip().split()[1:]  # skip "/savestring"
    if not raw:
        await session.send_message("⚠️ Usage: /savestring [filename] <text>")
        return

    # If more than one word and first contains an extension, treat as filename
    if len(raw) >= 2 and raw[0].endswith((".txt", ".log", ".md")):
        filename, text = raw[0], " ".join(raw[1:])
    else:
        # generate timestamped filename
        ts = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{ts}_savestring.txt"
        text = " ".join(raw)

    # Determine save directory from config or fallback to tmp/
    cfg = config_loader()
    save_dir = cfg.get("telegram", {}).get("download_path", "tmp")
    full_dir = os.path.join(save_dir, "saved_strings")
    os.makedirs(full_dir, exist_ok=True)

    path = os.path.join(full_dir, filename)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        await session.send_message(f"✅ Saved to `{filename}`")
    except Exception as e:
        logger.exception("Error saving string")
        await session.send_message(f"❌ Failed to save: {e}")
