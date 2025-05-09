# src/llm_telegram_bot/commands/handlers/history.py

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
      • off:   turn logging off & flush now
      • files: list saved history files
      • load:  load last history into context & manager
      • flush: flush current tier-0 into disk now
    """
    sess = get_session(session.chat_id, session.bot_name)
    mgr = session.history_mgr
    bot = session.bot_name

    status = "on ✅" if sess.history_on else "off ⏸️"
    header = f"History is {status}"

    if not args:
        usage = escape("/h <on|off|files|load|flush>")
        return await session.send_message(f"{header}\n⚠️ Usage: {usage}", parse_mode="HTML")

    cmd = args[0].lower()

    # ─── ON ────────────────────────────────────────────────────────────────
    if cmd == "on":
        sess.history_on = True
        return await session.send_message(f"{header}\n✅ History logging enabled.", parse_mode="HTML")

    # ─── OFF ───────────────────────────────────────────────────────────────
    if cmd == "off":
        sess.history_on = False
        # flush everything existing
        path = sess.flush_history_to_disk()
        # also clear manager tiers
        mgr.tier0.clear()
        mgr.tier1.clear()
        mgr.tier2.clear()
        return await session.send_message(
            f"{header}\n✅ History logging disabled & flushed to <code>{path}</code>.",
            parse_mode="HTML",
        )

    # ─── FILES ────────────────────────────────────────────────────────────
    if cmd in ("files", "list"):
        d = Path("histories") / bot / str(session.chat_id)
        if not d.exists():
            return await session.send_message(f"{header}\n⚠️ No history directory found.", parse_mode="HTML")
        files = sorted(p.name for p in d.glob("*.json"))
        if not files:
            return await session.send_message(f"{header}\n⚠️ No history files found.", parse_mode="HTML")
        listing = "\n".join(files)
        return await session.send_message(f"{header}\n<b>Files:</b>\n<code>{listing}</code>", parse_mode="HTML")

    # ─── LOAD ─────────────────────────────────────────────────────────────
    if cmd == "load":
        try:
            # load into session.buffer
            path = sess.load_history_from_disk()
            # seed manager.tier0 from session.history_buffer
            mgr.tier0.clear()
            for entry in sess.history_buffer:
                # reconstruct Message dataclass from dict
                from llm_telegram_bot.session.history_manager import Message

                msg = Message(
                    ts=entry["ts"],
                    who=entry["who"],
                    lang=entry.get("lang", "unknown"),
                    text=entry["text"],
                    tokens_original=entry.get("tokens_original", 0),
                    tokens_compressed=entry.get("tokens_compressed", entry.get("tokens_original", 0)),
                )
                mgr.tier0.append(msg)
            return await session.send_message(
                f"{header}\n✅ Loaded history from <code>{path}</code>.", parse_mode="HTML"
            )
        except FileNotFoundError:
            return await session.send_message(f"{header}\n⚠️ No history file to load.", parse_mode="HTML")
        except Exception as e:
            logger.exception("[/h load] Failed to load history")
            return await session.send_message(f"{header}\n❌ Could not load history: {e}", parse_mode="HTML")

    # ─── FLUSH / SAVE ─────────────────────────────────────────────────────
    if cmd in ("flush", "save"):
        if not sess.history_on:
            return await session.send_message("⚠️ History is disabled.", parse_mode="HTML")
        if not mgr.tier0:
            return await session.send_message(f"{header}\n⚠️ No new messages to flush.", parse_mode="HTML")
        # convert current tier0 back into session.history_buffer format
        sess.history_buffer = [
            {
                "who": m.who,
                "ts": m.ts,
                "lang": m.lang,
                "text": m.text,
                "tokens_original": m.tokens_original,
                "tokens_compressed": m.tokens_compressed,
            }
            for m in mgr.tier0
        ]
        path = sess.flush_history_to_disk()
        # clear manager after flush
        mgr.tier0.clear()
        return await session.send_message(f"{header}\n✅ History flushed to <code>{path}</code>.", parse_mode="HTML")

    # ─── UNKNOWN ──────────────────────────────────────────────────────────
    return await session.send_message(f"{header}\n⚠️ Unknown subcommand: {cmd}", parse_mode="HTML")
