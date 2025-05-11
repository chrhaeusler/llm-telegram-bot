import time
from pathlib import Path
from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.config.schemas import BotConfig
from llm_telegram_bot.session.history_manager import Message
from llm_telegram_bot.session.session_manager import get_session
from llm_telegram_bot.utils.logger import logger


@register_command("/slp")
async def slp_handler(session: Any, message: dict, args: List[str]) -> None:
    """
    /slp [<filename>]
    Save the last user prompt (from tier-0) into a timestamped file.
    """
    sess = get_session(session.chat_id, session.bot_name)
    mgr = sess.history_mgr

    # 1) Find the last user Message in tier0
    last_user: Message | None = None
    for msg in reversed(mgr.tier0):
        if msg.who == sess.active_user_data.get("identity", {}).get("name"):
            last_user = msg
            break
    if not last_user:
        return await session.send_message("⚠️ No user prompt found in recent history.")

    prompt_text = last_user.text
    ts = time.strftime("%Y-%m-%d_%H-%M-%S")

    # 2) Build filename
    base = Path(args[0]).name if args else "saved-prompt.txt"
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
        full.write_text(prompt_text, encoding="utf-8")
        logger.info(f"[slp] Saved last prompt to {full}")
        await session.send_message(f"✅ Saved last prompt as `{fname}`")
    except Exception as e:
        logger.exception("[slp] Error saving prompt")
        await session.send_message(f"❌ Could not save: {e}")
