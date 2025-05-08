# src/llm_telegram_bot/commands/handlers/user.py

from pathlib import Path
from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.session.session_manager import (
    get_active_user,
    get_session,
    set_active_user,
)
from llm_telegram_bot.utils.logger import logger

# Log that the user handler is being loaded
logger.info("[User Handler] user.py is being loaded")


@register_command("/user")
async def user_handler(session: Any, message: dict, args: List[str]):
    """
    /user [list|show|drop|<name>|<index>]
    Manage the active user YAML for this bot.
    """
    bot_name = session.bot_name
    # Directory where user yamls live
    users_dir = Path("config") / "users"

    # 1) List available user names
    files = sorted([f.stem for f in users_dir.glob("*.yaml") if f.is_file()])
    if not args or args[0].lower() == "show":
        current_user = get_active_user(session.chat_id, bot_name)
        # logging
        logger.debug(f"Current active char: {current_user}")
        logger.debug(f"Active char data: {session.active_user_data}")
        if current_user and session.active_user_data:
            user_data = session.active_user_data
            name = user_data.get("identity", {}).get("name", "(unknown)")
            role = user_data.get("role", "(unknown)")
            text = f"🔍 Current user:\n<b>Name:</b> {name}\n<b>Role:</b> {role}\n<b>File:</b> <code>{users_dir}/{current_user}.yaml</code>"
            await session.send_message(text, parse_mode="HTML")
        else:
            await session.send_message("⚠️ No character selected.")
        return

    cmd = args[0].lower()

    if cmd == "list":
        if not files:
            await session.send_message("⚠️ No User files found.")
        else:
            lines = ["<b>Available users:</b>"]
            active_user = session.active_user

            for i, name in enumerate(files):
                if name == active_user:
                    lines.append(f"<b>{i+1}. {name}</b>👈")
                else:
                    lines.append(f"{i+1}. {name}")

            await session.send_message("\n".join(lines), parse_mode="HTML")
        return

    # TO DO: this does not work
    if cmd == "drop":
        set_active_user(session.chat_id, bot_name, None)
        await session.send_message("✅ User selection cleared.")
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
            await session.send_message(f"⚠️ User not found: {cmd}")
            return

    # 3) Commit selection
    # Flush history first
    state = get_session(session.chat_id, session.bot_name)
    state.flush_history_to_disk()
    set_active_user(session.chat_id, bot_name, choice)
    await session.send_message(f"✅ Switched user to `{choice}`")
