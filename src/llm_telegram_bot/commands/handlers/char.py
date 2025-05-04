# src/llm_telegram_bot/commands/handlers/char.py

from pathlib import Path
from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.session.session_manager import (
    get_active_char,
    set_active_char,
)
from llm_telegram_bot.utils.logger import logger

# Log that the char handler is being loaded
logger.info("[Char Handler] char.py is being loaded")


@register_command("/char")
async def char_handler(session: Any, message: dict, args: List[str]):
    """
    /char [list|show|drop|<name>|<index>]
    Manage the active character YAML for this bot.
    """
    bot_name = session.client.bot_name
    # Directory where character yamls live
    chars_dir = Path("config") / "chars"

    # 1) List available char names
    files = sorted([f.stem for f in chars_dir.glob("*.yaml") if f.is_file()])
    if not args or args[0].lower() == "show":
        current = get_active_char(session.chat_id, bot_name)
        text = f"🔍 Current character: `{current}`" if current else "⚠️ No character selected."
        await session.send_message(text)
        return

    cmd = args[0].lower()

    if cmd == "list":
        if not files:
            await session.send_message("⚠️ No character files found.")
        else:
            lines = ["<b>Available characters:</b>"] + [f"{i+1}. {n}" for i, n in enumerate(files)]
            await session.send_message("\n".join(lines), parse_mode="HTML")
        return

    if cmd == "drop":
        set_active_char(session.chat_id, bot_name, None)
        await session.send_message("✅ Character selection cleared.")
        return

    # 2) Switch by index
    if cmd.isdigit():
        idx = int(cmd) - 1
        if 0 <= idx < len(files):
            choice = files[idx]
        else:
            await session.send_message(f"⚠️ Index out of range: {cmd}")
            return
    else:
        if cmd in files:
            choice = cmd
        else:
            await session.send_message(f"⚠️ Character not found: {cmd}")
            return

    # 3) Commit selection
    set_active_char(session.chat_id, bot_name, choice)
    await session.send_message(f"✅ Switched character to `{choice}`")

    # Alias: `/chars` → list characters
    @register_command("/chars")
    async def chars_alias(session: Any, message: dict, args: List[str]):
        # Force the “list” action
        from llm_telegram_bot.commands.handlers.char import char_handler

        await char_handler(session, message, ["list"])
