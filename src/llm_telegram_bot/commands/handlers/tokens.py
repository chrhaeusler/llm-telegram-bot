# src/commands/handlers/tokens.py

from typing import Any, Dict, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.session.session_manager import (
    get_max_tokens,
    set_max_tokens,
)
from llm_telegram_bot.utils.escape_html import html_escape
from llm_telegram_bot.utils.logger import logger

# Log that the help handler is being loaded
logger.info("[Tokens Handler] tokens.py is being loaded")


@register_command("/tokens")
async def tokens_handler(session: Any, message: Dict[str, Any], args: List[str]) -> None:
    """
    /tokens [<value>]
    Show or set the current token limit for the LLM model:
      • no value: show current tokens
      • <value>: set token limit to <value>
    """
    chat_id = session.chat_id
    bot_name = session.bot_name

    if not args:
        # No argument, show current tokens
        current_tokens = get_max_tokens(chat_id, bot_name)
        if current_tokens is None:
            current_tokens = load_config()["telegram"][session.client.bot_name]["default"].get("maxtoken", 4096)

        await session.send_message(
            f"Current token limit: <b>{html_escape(str(current_tokens))}</b>",
            parse_mode="HTML",
        )
        return

    try:
        # Try to parse the argument as an integer
        new_tokens = int(args[0])
    except ValueError:
        await session.send_message(
            "⚠️ Invalid token value. Please provide a valid integer.",
            parse_mode="HTML",
        )
        return

    # Set new token limit
    set_max_tokens(chat_id, bot_name, new_tokens)

    await session.send_message(
        f"✅ Token limit has been set to <b>{html_escape(str(new_tokens))}</b>",
        parse_mode="HTML",
    )
