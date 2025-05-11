import time
from pathlib import Path
from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.config.schemas import BotConfig
from llm_telegram_bot.session.history_manager import Message
from llm_telegram_bot.session.session_manager import get_session
from llm_telegram_bot.utils.logger import logger


@register_command("/slr")
async def slr_handler(session: Any, message: dict, args: List[str]) -> None:
    """
    /slr [<filename>]
    Save the last LLM response (from tier-0) into a timestamped file.
    """
    sess = get_session(session.chat_id, session.bot_name)
    mgr = sess.history_mgr

    # 1) Find the last bot Message in tier0
    last_bot: Message | None = None
    for msg in reversed(mgr.tier0):
        if msg.who == sess.active_char_data.get("identity", {}).get("name"):
            last_bot = msg
            break
    if not last_bot:
        return await session.send_message("⚠️ No LLM response found in recent history.")

    response_text = last_bot.text
    ts = time.strftime("%Y-%m-%d_%H-%M-%S")

    # 2) Build filename
    base = Path(args[0]).name if args else "saved-response.txt"
    fname = f"{ts}_{base}"

    # 3) Determine output directory from config
    cfg = load_config()
    tg_cfg = cfg.telegram
    bot_conf: BotConfig | None = tg_cfg.bots.get(session.bot_name)
    if not bot_conf:
        return await session.send_message("❌ Bot configuration not found.")

    root = bot_conf.download_path or tg_cfg.download_path
    outdir = Path(root) / session.bot_name / str(session.chat_id)
    outdir.mkdir(parents=True, exist_ok=True)
    full = outdir / fname

    # 4) Write to disk
    try:
        full.write_text(response_text, encoding="utf-8")
        logger.info(f"[slr] Saved last response to {full}")
        await session.send_message(f"✅ Saved last response as `{fname}`")
    except Exception as e:
        logger.exception("[slr] Error saving response")
        await session.send_message(f"❌ Could not save: {e}")
