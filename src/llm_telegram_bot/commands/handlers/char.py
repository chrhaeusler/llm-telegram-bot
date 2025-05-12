# src/llm_telegram_bot/commands/handlers/char.py

from datetime import datetime
from pathlib import Path
from typing import Any, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.session.history_manager import Message
from llm_telegram_bot.session.session_manager import (
    get_active_char,
    get_session,
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

    # 2) Determine choice
    if cmd.isdigit():
        idx = int(cmd) - 1
        if 0 <= idx < len(files):
            choice = files[idx]
        else:
            return await session.send_message(f"⚠️ Index out of range: {cmd}")
    else:
        if cmd in files:
            choice = cmd
        else:
            return await session.send_message(f"⚠️ Char not found: {cmd}")

    # 3) Commit selection
    state = get_session(session.chat_id, session.bot_name)

    # 3a) If logging is on, flush only the new tier-0 messages
    if state.history_on:
        new_entries: list[dict] = []
        last_ts = datetime.fromisoformat(state.last_load_ts)

        for msg in session.history_mgr.tier0:
            # Parse your msg.ts into a datetime
            try:
                msg_ts = datetime.strptime(msg.ts, "%Y-%m-%d_%H-%M-%S")
            except ValueError:
                logger.warning(f"Couldn’t parse msg.ts: {msg.ts}, skipping")
                continue

            # Only collect messages after the last load watermark
            if msg_ts > last_ts:
                new_entries.append(
                    {
                        "ts": msg.ts,
                        "who": msg.who,
                        "lang": msg.lang,
                        "text": msg.text,
                        "tokens_text": msg.tokens_text,
                        "tokens_compressed": msg.tokens_compressed,
                    }
                )

        if new_entries:
            logger.debug(f"[CharSwitch] New entries to flush: {len(new_entries)}")
            # prime the session buffer with only those new entries
            state.history_buffer = new_entries
            path = state.flush_history_to_disk()  # this clears history_buffer
            await session.send_message(
                f"🔄 Flushed {len(new_entries)} new messages to <code>{path}</code>",
                parse_mode="HTML",
            )

    # 3b) Actually switch the persona
    set_active_char(session.chat_id, session.bot_name, choice)
    await session.send_message(f"✅ Switched character to `{choice}`")

    # 3c) Clear in-memory tiers so we start fresh
    session.history_mgr.tier0.clear()
    session.history_mgr.tier1.clear()
    session.history_mgr.tier2.clear()

    # 3d) Load the new combo’s history from disk
    try:
        history_path = state.load_history_from_disk()
        # 3e) Stamp the watermark
        print(f"[DEBUG] Setting last_load_ts to {datetime.now().isoformat(timespec='seconds')}")
        state.last_load_ts = datetime.now().isoformat(timespec="seconds")
        print(f"[DEBUG] Starting char switch, last_load_ts = {state.last_load_ts}")

        # 3f) Seed tier-0 from what we just loaded
        for entry in state.history_buffer:
            msg = Message(
                ts=entry["ts"],
                who=entry["who"],
                lang=entry.get("lang", "unknown"),
                text=entry["text"],
                tokens_text=entry.get("tokens_text", 0),
                compressed=entry.get("compressed", entry["text"]),
                tokens_compressed=entry.get("tokens_compressed", entry.get("tokens_text", 0)),
            )
            session.history_mgr.tier0.append(msg)

        # 3g) Clear the legacy buffer so future flushes only send new messages
        state.history_buffer.clear()

        await session.send_message(
            f"✅ Loaded history from <code>{history_path}</code>",
            parse_mode="HTML",
        )

    except FileNotFoundError:
        # No prior history file → fresh start
        state.history_buffer.clear()
        state.last_load_ts = datetime.now().isoformat(timespec="seconds")
        await session.send_message("ℹ️ No prior history found; starting with a clean slate.")
