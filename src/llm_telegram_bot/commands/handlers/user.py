# src/llm_telegram_bot/commands/handlers/user.py

from pathlib import Path
from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.session.session_manager import (
    get_active_user,
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
    bot_name = session.client.bot_name
    # Directory where user yamls live
    users_dir = Path("config") / "users"

    # 1) List available user names
    files = sorted([f.stem for f in users_dir.glob("*.yaml") if f.is_file()])
    if not args or args[0].lower() == "show":
        current = get_active_user(session.chat_id, bot_name)
        text = f"🔍 Current user: `{current}`" if current else "⚠️ No user selected."
        await session.send_message(text)
        return

    cmd = args[0].lower()

    if cmd == "list":
        if not files:
            await session.send_message("⚠️ No user files found.")
        else:
            lines = ["<b>Available users:</b>"] + [f"{i+1}. {n}" for i, n in enumerate(files)]
            await session.send_message("\n".join(lines), parse_mode="HTML")
        return

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
    set_active_user(session.chat_id, bot_name, choice)
    await session.send_message(f"✅ Switched user to `{choice}`")

    # Alias: `/users` → list users
    @register_command("/users")
    async def users_alias(session: Any, message: dict, args: List[str]):
        """
        Alias for `/user list`
        """
        # reuse the main handler, forcing the "list" subcommand
        from llm_telegram_bot.commands.handlers.user import user_handler

        await user_handler(session, message, ["list"])
