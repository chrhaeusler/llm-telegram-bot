# src/telegram/routing.py

import logging
from typing import Any, Dict

from src.commands.commands_registry import (
    dummy_handler,
    get_command_handler,
    is_command_implemented,
)

logger = logging.getLogger(__name__)


async def route_message(session: Any, message: Dict[str, Any]) -> None:
    """
    Routes an incoming Telegram message to the appropriate command handler.

    Args:
      session:    A ChatSession-like object with a `send_message(text: str)` method.
      message:    The Telegram 'message' dict (expects 'text' and 'chat':{'id':...}).
    """
    # Extract text and chat_id
    text = message.get("text", "")
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if chat_id is None:
        logger.warning("[Routing] No chat.id in message, skipping.")
        return

    if not text:
        logger.warning(f"[Routing] Empty text from chat {chat_id}, skipping.")
        return

    logger.info(f"[Routing] chat={chat_id} → '{text}'")

    command_name = text.strip().split()[0]
    handler = get_command_handler(command_name)

    try:
        if handler:
            # Execute the handler
            logger.debug(f"[Routing] Calling handler for '{command_name}'")
            result = await handler(session=session, message=message)
            if result:
                await session.send_message(result)

        elif is_command_implemented(command_name):
            # Known but not yet implemented
            logger.debug(f"[Routing] Known but unimplemented '{command_name}'")
            result = await dummy_handler(session=session, message=message)
            if result:
                await session.send_message(result)

        else:
            # Unknown command
            logger.info(f"[Routing] Unknown command '{command_name}'")
            await session.send_message(
                f"⚠️ Unknown command: {command_name}\nSend /help for a list."
            )

    except Exception:
        logger.exception(f"[Routing] Exception while routing '{command_name}'")
        # Notify the user
        await session.send_message(
            "❌ An internal error occurred while processing your command."
        )
