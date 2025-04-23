# src/telegram/routing.py

import logging
from typing import Any, Awaitable, Dict, List

from src.commands.commands_registry import (
    dummy_handler,
    get_command_handler,
    is_command_implemented,
)

logger = logging.getLogger(__name__)


async def route_message(
    session: Any,
    message: Dict[str, Any],
    llm_call: Awaitable,
    model: str,
    temperature: float,
    maxtoken: int,
) -> None:
    """
    Routes an incoming message to either:
      • a registered slash‐command handler, or
      • the LLM service for free‐text prompts.

    session       – any object with 'chat_id' attribute and an async 'send_message(text)'.
    message       – raw Telegram message dict (must include 'text' and 'chat':{'id':…}).
    llm_call      – coroutine: llm_call(prompt, model, temperature, maxtoken) → str
    model, temperature, maxtoken – LLM params for free‐text calls.
    """
    text = message.get("text", "").strip()
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    # keep session in sync
    if hasattr(session, "chat_id"):
        session.chat_id = chat_id

    if not text:
        logger.warning("[Routing] empty text; ignoring")
        return

    # ── Slash commands ────────────────────────────────────────────────────────────
    if text.startswith("/"):
        parts: List[str] = text.split()
        cmd = parts[0]
        args = parts[1:]

        handler = get_command_handler(cmd)
        if handler:
            logger.info(f"[Routing] ‹{cmd}› → command handler, args={args}")
            try:
                await handler(session=session, message=message, args=args)
            except Exception as e:
                logger.exception(f"[Routing] error in handler ‹{cmd}›: {e}")
                await session.send_message(f"❌ Error executing {cmd}: {e}")
        else:
            if is_command_implemented(cmd):
                logger.info(f"[Routing] ‹{cmd}› known but unimplemented")
                await dummy_handler(session=session, message=message, args=args)
            else:
                logger.info(f"[Routing] unknown command ‹{cmd}›")
                await session.send_message(
                    f"⚠️ Unknown command: {cmd}\nSend /help for a list."
                )
        return

    # ── Free-text → LLM ──────────────────────────────────────────────────────────
    logger.info("[Routing] Free-text input; sending to LLM…")
    try:
        reply = await llm_call(
            prompt=text, model=model, temperature=temperature, maxtoken=maxtoken
        )
        await session.send_message(reply)
    except Exception as e:
        logger.exception(f"[Routing] LLM call failed: {e}")
        await session.send_message(f"❌ LLM service error: {e}")
