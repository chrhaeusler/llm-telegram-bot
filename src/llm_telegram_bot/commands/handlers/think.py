# src/commands/handlers/think.py

from typing import Any, Dict, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.session.session_manager import (
    get_think_blocks_on,
    set_think_blocks_on,
)
from llm_telegram_bot.utils.logger import logger

logger.info("[Think Block Handler] think.py is being loaded")


@register_command("/think")
@register_command("/thinking")
async def think_handler(session: Any, message: Dict[str, Any], args: List[str]) -> None:
    """
    /think [on|off]
    Show or set whether the assistant sends <think> blocks:
      • no value: show current state
      • on/off: enable or disable <think> blocks
    """
    chat_id = session.chat_id
    bot_name = session.bot_name

    if not args:
        # No argument, show current state
        current_value = get_think_blocks_on(chat_id, bot_name)

        if current_value:
            status_reply = "<b>sent</b> to Telegram ✅"
        else:
            status_reply = "<b>not sent</b> to Telegram ❌"

        await session.send_message(
            "Think blocks are " + status_reply,
            parse_mode="HTML",
        )
        return

    arg = args[0].strip().lower()
    if arg not in ("on", "off"):
        await session.send_message(
            "⚠️ Invalid argument. Use <code>/think on</code> or <code>/think off</code>.",
            parse_mode="HTML",
        )
        return

    new_value = arg == "on"
    set_think_blocks_on(chat_id, bot_name, new_value)

    await session.send_message(
        f"✅ <b>Think blocks</b> have been turned <b>{'ON' if new_value else 'OFF'}</b>.",
        parse_mode="HTML",
    )
