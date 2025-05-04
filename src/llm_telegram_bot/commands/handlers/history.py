from pathlib import Path
from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.session.session_manager import get_session
from llm_telegram_bot.utils.logger import logger

logger.info("[History Handler] history.py loaded")


@register_command("/history")
async def history_handler(session: Any, message: dict, args: List[str]):
    """
    /history on|off|files|load|new
      • on:    turn logging on
      • off:   turn logging off & flush
      • files: list saved history files
      • load:  load a file into context
      • new:   flush & start a new file
    """
    sess = get_session(session.chat_id, session.client.bot_name)
    bot = session.client.bot_name

    # Always show current state first
    status = "✅ ON" if sess.history_on else "⏸️ OFF"
    header = f"<b>History:</b> {status}"
    if not args:
        return await session.send_message(
            f"{header}\n⚠️ Usage: /history &lt;on|off|files|load|new&gt;", parse_mode="HTML"
        )

    cmd = args[0].lower()

    if cmd == "on":
        sess.history_on = True
        return await session.send_message(f"{header}\n✅ History logging enabled.", parse_mode="HTML")

    if cmd == "off":
        sess.history_on = False
        sess.flush_history_to_disk(bot)
        return await session.send_message(f"{header}\n✅ History logging disabled & flushed.", parse_mode="HTML")

    # List files; create alias "/histories" for that
    if cmd == "list":
        d = Path("histories") / bot / str(session.chat_id)
        if not d.exists():
            return await session.send_message(f"{header}\n⚠️ No history directory found.", parse_mode="HTML")
        files = sorted(p.name for p in d.glob("*.json"))
        if not files:
            return await session.send_message(f"{header}\n⚠️ No history files found.", parse_mode="HTML")
        listing = "\n".join(files)
        return await session.send_message(f"{header}\n<b>Files:</b>\n{listing}", parse_mode="HTML")

    # will need to switch char and user depending on the loaded file
    if cmd == "load":
        session.send_message(f"{header}\n⚠️ /history load not implemented yet.", parse_mode="HTML")

    # is this necessary? imo, this should be "save" to manually trigger updating the file
    if cmd == "new":
        sess.flush_history_to_disk(bot)
        sess.history_on = True
        return await session.send_message(f"{header}\n✅ Started new history file.", parse_mode="HTML")

    return await session.send_message(f"{header}\n⚠️ Unknown subcommand: {cmd}", parse_mode="HTML")
