# src/commands/handlers/history.py

from html import escape
from pathlib import Path
from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.session.session_manager import (
    get_session,
)
from llm_telegram_bot.utils.logger import logger

logger.info("[History Handler] history.py loaded")


@register_command("/h")
async def history_handler(session: Any, message: dict, args: List[str]):
    """
    /h on|off|files|load|flush
      • on:    turn logging on
      • off:   turn logging off & flush
      • files: list saved history files
      • load:  load a file into context
      • flush: flush/write history to file now
    """
    sess = get_session(session.chat_id, session.bot_name)
    bot = session.bot_name

    # Always show current state first
    status = "on ✅" if sess.history_on else "off ⏸️"
    header = f"<b>History:</b> is {status}"

    if not args:
        usage = escape("/h <on|off|files|load|flush>")
        return await session.send_message(
            f"{header}\n⚠️ Usage: {usage}",
            parse_mode="HTML",
        )

    cmd = args[0].lower()

    if cmd == "on":
        sess.history_on = True
        return await session.send_message(f"{header}\n✅ History logging enabled.", parse_mode="HTML")

    if cmd == "off":
        sess.history_on = False
        path = sess.flush_history_to_disk()
        return await session.send_message(
            f"{header}\n✅ History logging disabled & flushed to <code>{path}</code>.",
            parse_mode="HTML",
        )

    if cmd == "files":
        d = Path("histories") / bot / str(session.chat_id)
        if not d.exists():
            return await session.send_message(f"{header}\n⚠️ No history directory found.", parse_mode="HTML")
        files = sorted(p.name for p in d.glob("*.json"))
        if not files:
            return await session.send_message(f"{header}\n⚠️ No history files found.", parse_mode="HTML")
        listing = "\n".join(files)
        return await session.send_message(f"{header}\n<b>Files:</b>\n<code>{listing}</code>", parse_mode="HTML")

    if cmd in ("flush", "save"):
        if not sess.history_on:
            return await session.send_message("⚠️ History is disabled.")
        if not sess.history_buffer:
            return await session.send_message("⚠️ No new history to flush.")
        path = sess.flush_history_to_disk()
        return await session.send_message(f"{header}\n✅ History flushed to <code>{path}</code>.", parse_mode="HTML")

    if cmd == "load":
        # Attempt to load history from disk using the session's method
        try:
            # Call the method from the session to load history
            path = sess.load_history_from_disk()

            return await session.send_message(
                f"{header}\n✅ Loaded history from <code>{path}</code>.", parse_mode="HTML"
            )
        except FileNotFoundError:
            return await session.send_message(f"{header}\n⚠️ No history file to load.", parse_mode="HTML")
        except Exception as e:
            logger.exception("[/h load] Failed to load history")
            return await session.send_message(f"{header}\n❌ Could not load history: {e}", parse_mode="HTML")

    # unknown command
    return await session.send_message(f"{header}\n⚠️ Unknown subcommand: {cmd}", parse_mode="HTML")
