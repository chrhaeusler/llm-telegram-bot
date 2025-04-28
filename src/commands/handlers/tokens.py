# src/commands/handlers/tokens.py

import logging
from typing import Any, Dict, List

from src.commands.commands_registry import register_command
from src.config_loader import config_loader
from src.session.session_manager import (
    get_maxtoken,
    set_maxtoken,
)
from src.utils.escape_html import html_escape

logger = logging.getLogger(__name__)
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

    if not args:
        # No argument, show current tokens
        current_tokens = get_maxtoken(chat_id)
        if current_tokens is None:
            current_tokens = config_loader()["telegram"][session.client.bot_name]["default"].get("maxtoken", 4096)

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
    set_maxtoken(chat_id, new_tokens)

    await session.send_message(
        f"✅ Token limit has been set to <b>{html_escape(str(new_tokens))}</b>",
        parse_mode="HTML",
    )
