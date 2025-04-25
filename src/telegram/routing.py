# src/telegram/routing.py

import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from src.commands.commands_registry import get_command_handler
from src.config_loader import config_loader
from src.session.session_manager import get_session, is_paused

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,  # Ensure DEBUG messages are logged
    format="%(asctime)s - %(levelname)s - %(message)s",
)


async def route_message(
    session: Any,
    message: Dict[str, Any],
    llm_call: Optional[
        Callable[[str, Optional[str], float, int], Awaitable[str]]
    ] = None,
    model: str = "",
    temperature: float = 0.7,
    maxtoken: int = 1024,
) -> None:
    """
    Routes an incoming message to either:
      • a registered slash‐command handler, or
      • the LLM service for free‐text prompts.
    """
    text = message.get("text", "").strip()
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    # Sync chat_id if session supports it
    if hasattr(session, "chat_id"):
        session.chat_id = chat_id

    if not text:
        logger.warning("[Routing] empty text; ignoring")
        return

    if text.startswith("/"):
        parts = text.split()
        raw = parts[0]  # '/help' or '/help@BotName'
        args = parts[1:]

        cmd = raw.lstrip("/")
        if "@" in cmd:
            cmd = cmd.split("@", 1)[0]

        # Log and check for handler
        logger.info(f"[Routing] Checking for handler for command: /{cmd}")
        handler = get_command_handler(cmd)

        if handler:
            logger.info(f"[Routing] ‹/{cmd}› → command handler, args={args}")
            try:
                await handler(session, message, args)
            except Exception as e:
                logger.exception(f"[Routing] error in handler ‹/{cmd}›: {e}")
                await session.send_message(f"❌ Error executing /{cmd}: {e}")
        else:
            logger.warning(f"[Routing] Command handler not found for ‹/{cmd}›")
            await session.send_message(
                f"⚠️ Unknown command: /{cmd}\nSend /help for a list."
            )
        return

    # ── Free-text → LLM ──────────────────────────────────────────────────────

    if is_paused(session.chat_id):
        logger.info(
            f"[Routing] Messaging paused for chat {session.chat_id} — skipping LLM"
        )
        return

    logger.info("[Routing] Free-text input; sending to LLM…")

    try:
        # Dynamically override model from active service (if set)
        real_session = get_session(
            chat_id
        )  # ensures we have our internal Session object
        if real_session.active_service:
            config = config_loader()
            service_conf = config.get("services", {}).get(
                real_session.active_service, {}
            )
            model = service_conf.get("model", model)

            logger.debug(
                f"[Routing] Using overridden service: {real_session.active_service}, model: {model}"
            )
        else:
            logger.debug(f"[Routing] Using default model: {model}")

        # Guard: only call llm_call if it’s provided
        if llm_call is None:
            logger.error("No LLM-call function passed for free-text; skipping.")
            return
        reply = await llm_call(text, model, temperature, maxtoken)

        await session.send_message(reply)

    except Exception as e:
        logger.exception(f"[Routing] LLM call failed: {e}")
        await session.send_message(f"❌ LLM service error: {e}")
