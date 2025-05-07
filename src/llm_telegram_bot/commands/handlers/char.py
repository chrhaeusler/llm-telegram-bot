# src/llm_telegram_bot/commands/handlers/char.py

from pathlib import Path
from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.session.session_manager import (
    get_active_char,
    set_active_char,
)
from llm_telegram_bot.utils.logger import logger
from llm_telegram_bot.utils.message_utils import split_message

# Log that the char handler is being loaded
logger.info("[char Handler] char.py is being loaded")


@register_command("/char")
async def char_handler(session: Any, message: dict, args: List[str]):
    """
    /char [list|show|drop|<name>|<index>]
    Manage the active char YAML for this bot.
    """
    bot_name = session.bot_name
    # Directory where char yamls live
    chars_dir = Path("config") / "chars"

    # Available char names
    files = sorted([f.stem for f in chars_dir.glob("*.yaml") if f.is_file()])

    if not args or args[0].lower() == "show":
        current = get_active_char(session.chat_id, bot_name)
        # logging
        logger.debug(f"Current active char: {current}")
        logger.debug(f"Active char data: {session.active_char_data}")
        if current and session.active_char_data:
            char_data = session.active_char_data
            char_name = char_data.get("identity", {}).get("name", "(unknown)")
            role = char_data.get("role", "(unknown)")
            text = f"🔍 Current character:\n<b>Name:</b> {char_name}\n<b>Role:</b> {role}\n<b>File:</b> <code>{chars_dir}/{current}.yaml</code>"

            if len(text) > 4096:
                logger.warning(f"[Char Handler] Splitting description of {current}")

                for chunk in split_message(text):
                    await session.send_message(chunk, parse_mode="HTML")

            await session.send_message(text, parse_mode="HTML")
        else:
            await session.send_message("⚠️ No character selected.")
        return

    cmd = args[0].lower()
    # List
    if cmd == "list":
        if not files:
            await session.send_message("⚠️ No Char files found.")
        else:
            lines = ["<b>Available chars:</b>"]
            active_char = session.active_char

            for i, name in enumerate(files):
                if name == active_char:
                    lines.append(f"<b>{i+1}. {name}</b>👈")
                else:
                    lines.append(f"{i+1}. {name}")

            await session.send_message("\n".join(lines), parse_mode="HTML")
        return

    # Drop char (char = NONE)
    if cmd == "drop":
        set_active_char(session.chat_id, bot_name, None)
        await session.send_message("✅ Char selection cleared.")
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
            await session.send_message(f"⚠️ Char not found: {cmd}")
            return

    # 3) Commit selection
    set_active_char(session.chat_id, bot_name, choice)
    await session.send_message(f"✅ Switched Char to `{choice}`")

    # Alias: `/chars` → list chars
    @register_command("/chars")
    async def chars_alias(session: Any, message: dict, args: List[str]):
        """
        Alias for `/char list`
        """
        # reuse the main handler, forcing the "list" subcommand
        from llm_telegram_bot.commands.handlers.char import char_handler

        await char_handler(session, message, ["list"])
