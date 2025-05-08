# src/commands/handlers/history.py

from html import escape
from pathlib import Path
from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.session.session_manager import get_session
from llm_telegram_bot.utils.logger import logger

logger.info("[History Handler] history.py loaded")


@register_command("/h")
@register_command("/history")
async def history_handler(session: Any, message: dict, args: List[str]):
    """
    /h on|off|files|load|flush
      • on:    turn logging on
      • off:   turn logging off & flush
      • files: list saved history files
      • load:  load the single history file into memory
      • flush: write any buffered history out now
    """
    sess = get_session(session.chat_id, session.bot_name)
    bot_name = session.bot_name

    # Header with current state
    status = "on ✅" if sess.history_on else "off ⏸️"
    header = f"<b>History:</b> is {status}"

    # No args → show usage
    if not args:
        usage = escape("/h <on|off|files|load|flush>")
        return await session.send_message(
            f"{header}\n⚠️ Usage: {usage}",
            parse_mode="HTML",
        )

    cmd = args[0].lower()

    # ─── on ───────────────────────────────────────────────────────────────
    if cmd == "on":
        sess.history_on = True
        return await session.send_message(
            f"{header}\n✅ History logging enabled.",
            parse_mode="HTML",
        )

    # ─── off ──────────────────────────────────────────────────────────────
    if cmd == "off":
        sess.history_on = False
        try:
            path = sess.flush_history_to_disk()
            path_txt = escape(str(path))
        except Exception as e:
            logger.exception("[/h off] flush failed")
            return await session.send_message(
                f"{header}\n❌ Failed to flush history: {escape(str(e))}",
                parse_mode="HTML",
            )
        return await session.send_message(
            f"{header}\n✅ History logging disabled & flushed to <code>{path_txt}</code>.",
            parse_mode="HTML",
        )

    # ─── files ────────────────────────────────────────────────────────────
    if cmd == "files":
        d = Path("histories") / bot_name / str(session.chat_id)
        if not d.exists():
            return await session.send_message(
                f"{header}\n⚠️ No history directory found.",
                parse_mode="HTML",
            )
        files = sorted(p.name for p in d.glob("*.json"))
        if not files:
            return await session.send_message(
                f"{header}\n⚠️ No history files found.",
                parse_mode="HTML",
            )
        listing = "\n".join(escape(f) for f in files)
        return await session.send_message(
            f"{header}\n<b>Files:</b>\n<code>{listing}</code>",
            parse_mode="HTML",
        )

    # ─── load ─────────────────────────────────────────────────────────────
    if cmd == "load":
        try:
            path = sess.load_history_from_disk()
            path_txt = escape(path)
            return await session.send_message(
                f"{header}\n✅ Loaded history from <code>{path_txt}</code>.",
                parse_mode="HTML",
            )
        except FileNotFoundError:
            return await session.send_message(
                f"{header}\n⚠️ No history file to load.",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.exception("[/h load] Failed to load history")
            return await session.send_message(
                f"{header}\n❌ Could not load history: {escape(str(e))}",
                parse_mode="HTML",
            )

    # ─── flush ────────────────────────────────────────────────────────────
    if cmd in ("flush", "save"):
        if not sess.history_on:
            return await session.send_message(
                "⚠️ History is disabled.",
                parse_mode="HTML",
            )
        # use the HistoryManager on the ChatSession itself:
        mgr = session.history_mgr
        if not mgr.tier0:
            return await session.send_message(
                "⚠️ No new history to flush.",
                parse_mode="HTML",
            )
        # first flush the old buffer if you still need it:
        path = sess.flush_history_to_disk()
        # (optionally, implement mgr.flush() later to write out tier1/tier2)
        return await session.send_message(
            f"{header}\n✅ History flushed to <code>{path}</code>.",
            parse_mode="HTML",
        )

    # ─── unknown ──────────────────────────────────────────────────────────
    return await session.send_message(
        f"{header}\n⚠️ Unknown subcommand: {escape(cmd)}",
        parse_mode="HTML",
    )
