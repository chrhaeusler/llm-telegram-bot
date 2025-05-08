# src/llm_telegram_bot/commands/handlers/savelastprompt.py

import os
import time
from pathlib import Path
from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.config.schemas import BotConfig
from llm_telegram_bot.session.session_manager import get_memory
from llm_telegram_bot.utils.logger import logger


@register_command("/slp")
async def slp_handler(session: Any, message: dict, args: List[str]) -> None:
    """
    /slp [<filename>]
    Save the last user prompt from memory into a timestamped file.
    """
    # 1) Fetch last prompt
    mem = get_memory(session.chat_id, session.bot_name).get("last_prompt", [])
    if not mem:
        return await session.send_message("⚠️ No prompt in memory to save.")
    prompt = mem[-1]

    ts = time.strftime("%Y-%m-%d_%H-%M-%S")

    # 2) Determine filename
    if args:
        base = Path(args[0]).name
        fname = f"{ts}_{base}"
    else:
        fname = f"{ts}_saved-prompt.txt"

    # 3) Determine output directory from config
    cfg = load_config()  # RootConfig
    tg_cfg = cfg.telegram  # TelegramConfig
    bot_conf: BotConfig | None = tg_cfg.bots.get(session.client.bot_name)
    if not bot_conf:
        return await session.send_message("❌ Bot configuration not found.")

    # Use bot-level download_path, or fallback to global
    root = bot_conf.download_path or tg_cfg.download_path
    bot_nr = session.bot_name
    outdir = os.path.join(root, bot_nr, str(session.chat_id))
    os.makedirs(outdir, exist_ok=True)
    full = os.path.join(outdir, fname)

    # 4) Write to disk
    try:
        with open(full, "w", encoding="utf-8") as f:
            f.write(prompt)
        logger.info(f"[slp] Saved last prompt to {full}")
        await session.send_message(f"✅ Saved last prompt as `{fname}`")
    except Exception as e:
        logger.exception("[slp] Error saving prompt")
        await session.send_message(f"❌ Could not save: {e}")
