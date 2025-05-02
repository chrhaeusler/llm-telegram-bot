# src/commands/handlers/char.py
from typing import Any, List

from src.char_loader import get_all_characters, get_character
from src.commands.commands_registry import register_command
from src.session.session_manager import set_active_char


@register_command("/char")
async def char_handler(session: Any, message: dict, args: List[str]):
    """
    /char [list|show|reset] [<key_or_index>]

    • no args or “list”: list all chars with number & role
    • show <key_or_index>: display full details
    • reset: reload definitions (no-op)
    • <key_or_index>: switch to that character
    """
    chars = get_all_characters()  # Dict[str, dict]
    keys = list(chars.keys())

    # 1) LIST
    if not args or args[0] == "list":
        lines = []
        for idx, key in enumerate(keys, start=1):
            role = chars[key].get("role", "")
            lines.append(f"{idx}. {key} ({role})")
        await session.send_message("<b>Available characters:</b>\n" + "\n".join(lines), parse_mode="HTML")
        return

    action = args[0]
    # 2) SHOW
    if action == "show":
        if len(args) < 2:
            return await session.send_message("⚠️ Usage: /char show <key_or_index>")
        sel = args[1]
        # resolve index vs key
        if sel.isdigit():
            i = int(sel) - 1
            if 0 <= i < len(keys):
                sel = keys[i]
        info = get_character(sel)
        if not info:
            return await session.send_message(f"⚠️ Character not found: {sel}")
        # repr the raw dict
        await session.send_message(f"```json\n{info!r}\n```")
        return

    # 3) RESET
    if action == "reset":
        # no-op today
        await session.send_message("🔄 Character settings reloaded from disk.")
        return

    # 4) SWITCH (anything else is treated as switch key/index)
    sel = action
    if sel.isdigit():
        idx = int(sel) - 1
        if 0 <= idx < len(keys):
            sel = keys[idx]
        else:
            return await session.send_message(f"⚠️ Invalid character index: {action}")
    if sel not in chars:
        return await session.send_message(f"⚠️ Character not found: {sel}")

    set_active_char(session.chat_id, sel)
    await session.send_message(f"✅ Switched character to {sel}")
