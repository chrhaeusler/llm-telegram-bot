# src/commands/handlers/char.py

import html
import json
from typing import Any, List

from src.char_loader import get_all_characters, get_character
from src.commands.commands_registry import register_command
from src.session.session_manager import get_active_char, set_active_char


@register_command("/char")
async def char_handler(session: Any, message: dict, args: List[str]):
    """
    /char [list|show|reset|<key_or_index>]

    • no args: show current character
    • list: list all characters
    • show <key|index>: show full details of a character
    • reset: reload (no-op)
    • <key|index>: switch active character
    """
    chars = get_all_characters()  # type: dict[str, dict]
    keys = list(chars.keys())
    chat_id = session.chat_id

    # 1. No args → show current character
    if not args:
        current_key = get_active_char(chat_id)
        if not current_key:
            return await session.send_message("⚠️ No character selected. Use /char list.", parse_mode="HTML")

        info = get_character(current_key)
        if not info:
            return await session.send_message(
                f"⚠️ Current character not found: {html.escape(current_key)}", parse_mode="HTML"
            )

        identity = info.get("identity", {})
        lines = [
            "<b>🎭 Current Character</b>",
            f"• <b>Key:</b> {html.escape(current_key)}",
            f"• <b>Role:</b> {html.escape(info.get('role', ''))}",
            f"• <b>Description:</b> {html.escape(info.get('description', ''))}",
            f"• <b>Name:</b> "
            f"{html.escape(identity.get('name', ''))} "
            f"({html.escape(identity.get('first', ''))} "
            f"{html.escape(identity.get('last', ''))})",
            f"• <b>Age:</b> {html.escape(str(identity.get('age', '')))}",
            # f"• <b>Background:</b> {html.escape(identity.get('background', ''))})",
            # f"• <b>Skills:</b> {html.escape(identity.get('skills', ''))})",
            # f"• <b>Interests:</b> {html.escape(identity.get('interests', ''))})",
        ]
        await session.send_message("\n".join(lines), parse_mode="HTML")
        return

    action = args[0].lower()

    # 2. List
    if action == "list":
        lines = [
            f"{i}. {html.escape(k)} ({html.escape(chars[k].get('role', ''))})" for i, k in enumerate(keys, start=1)
        ]
        await session.send_message("<b>📜 Available Characters:</b>\n" + "\n".join(lines), parse_mode="HTML")
        return

    # 3. Reset (noop)
    if action == "reset":
        await session.send_message("🔄 Character settings reloaded from disk.")
        return

    # 4. Show
    if action == "show":
        if len(args) < 2:
            return await session.send_message("⚠️ Usage: /char show <key_or_index>", parse_mode="HTML")
        sel = args[1]
        if sel.isdigit():
            idx = int(sel) - 1
            if 0 <= idx < len(keys):
                sel = keys[idx]
        info = get_character(sel)
        if not info:
            return await session.send_message(f"⚠️ Character not found: {html.escape(sel)}", parse_mode="HTML")
        pretty = json.dumps(info, indent=2, ensure_ascii=False)
        await session.send_message(f"<pre>{html.escape(pretty)}</pre>", parse_mode="HTML")
        return

    # 5. Switch (default)
    sel = action
    if sel.isdigit():
        idx = int(sel) - 1
        if 0 <= idx < len(keys):
            sel = keys[idx]
        else:
            return await session.send_message(f"⚠️ Invalid character index: {html.escape(sel)}", parse_mode="HTML")
    if sel not in chars:
        return await session.send_message(f"⚠️ Character not found: {html.escape(sel)}", parse_mode="HTML")

    set_active_char(chat_id, sel)
    await session.send_message(f"✅ Switched character to <b>{html.escape(sel)}</b>", parse_mode="HTML")
