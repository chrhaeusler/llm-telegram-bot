# src/telegram/routing.py

from typing import Any, Awaitable, Callable, Dict, Optional

from llm_telegram_bot.commands.commands_registry import get_command_handler
from llm_telegram_bot.session.session_manager import get_session, is_paused
from llm_telegram_bot.telegram.poller import ChatSession
from llm_telegram_bot.utils.escape_html import html_escape
from llm_telegram_bot.utils.logger import logger


async def route_message(
    *,
    session: ChatSession,
    message: Dict[str, Any],
    llm_call: Optional[Callable[[str, str, float, int], Awaitable[str]]] = None,
    model: str = "",
    temperature: float = 0.7,
    maxtoken: int = 1024,
) -> None:
    """
    Routes an incoming Telegram message:
      • Slash command → dispatch to handler
      • Free-text → call LLM (if not paused)

    All outgoing text is HTML-escaped and sent in HTML mode.

    Args:
        session: ChatSession wrapper with send_message()
        message: Raw Telegram message dict
        llm_call: Coroutine function for LLM calls
        model: Default model name
        temperature: Sampling temperature
        maxtoken: Max tokens for LLM
    """
    text = message.get("text", "").strip()
    chat_id = session.chat_id

    if not text:
        logger.warning("[Routing] Empty text; ignoring.")
        return

    # ── Slash Commands ──────────────────────────────────────────────────────
    if text.startswith("/"):
        parts = text.split()
        raw = parts[0].lower()
        args = parts[1:]

        # all commands are lower case
        # catch annoying auto-correct capitalizing the text sometimes
        cmd = raw.lstrip("/").lower()  # catch
        if "@" in cmd:
            cmd = cmd.split("@", 1)[0]

        logger.info(f"[Routing] Handling command: /{cmd}")
        handler = get_command_handler(cmd)
        if handler:
            try:
                await handler(session=session, message=message, args=args)
            except Exception as e:
                logger.exception(f"[Routing] Error in handler /{cmd}: {e}")
                await session.send_message(html_escape(f"❌ Error executing /{cmd}: {e}"))
        else:
            await session.send_message(html_escape(f"⚠️ Unknown command: /{cmd}\nSend /help for a list."))
        return

    # ── Free-text → LLM ────────────────────────────────────────────────────
    if is_paused(chat_id):
        logger.info(f"[Routing] Messaging paused for chat {chat_id}")
        return

    if llm_call is None:
        logger.error("[Routing] No LLM call provided; skipping free-text.")
        return

    # Override model based on active service
    real_session = get_session(chat_id)
    svc = real_session.active_service
    if svc:
        from llm_telegram_bot.config.config_loader import load_config

        cfg = load_config()
        svc_conf = cfg.get("services", {}).get(svc, {})
        model = svc_conf.get("model", model)
        logger.debug(f"[Routing] Using service {svc}, model {model}")

    try:
        reply = await llm_call(text, model, temperature, maxtoken)
        await session.send_message(html_escape(reply))
    except Exception as e:
        logger.exception(f"[Routing] LLM call failed: {e}")
        await session.send_message(html_escape(f"❌ LLM service error: {e}"))
