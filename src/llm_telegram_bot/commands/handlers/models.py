# src/llm_telegram_bot/commands/handlers/models.py

from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.utils.logger import logger

logger.info("[Models Handler] models.py is being loaded")


@register_command("/bots")
async def bots_handler(session: Any, message: dict, args: List[str]) -> None:
    """
    /bots
    List all configured and enabled bots (display name and Telegram handle).
    """
    try:
        cfg = load_config()
        tg_cfg = cfg.telegram

        active_bot = session.bot_name
        bots_list: List[tuple[str, str, str]] = []  # (bot_name, display_name, handle)

        for bot_name, bot_conf in tg_cfg.bots.items():
            if not bot_conf.enabled:
                continue
            display_name = bot_conf.name or bot_name
            handle = bot_conf.handle or ""
            bots_list.append((bot_name, display_name, handle))

        if not bots_list:
            await session.send_message("⚠️ No bots configured or enabled.", parse_mode="HTML")
            return

        lines = ["<b>Configured and enabled bots:</b>"]
        for idx, (bot_name, display_name, handle) in enumerate(bots_list, start=1):
            prefix = f"<b>{idx}. {display_name}</b>" if bot_name == active_bot else f"{idx}. {display_name}"
            suffix = " 👈" if bot_name == active_bot else ""
            if handle:
                lines.append(f"{prefix} ({handle}){suffix}")
            else:
                lines.append(f"{prefix}{suffix}")

        await session.send_message("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        logger.exception("Error in /bots handler")
        await session.send_message(f"❌ Error executing /bots: <code>{e}</code>", parse_mode="HTML")
