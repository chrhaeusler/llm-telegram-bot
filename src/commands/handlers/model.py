# src/commands/handlers/model.py

import logging
from typing import Any, Dict, List

from src.commands.commands_registry import register_command
from src.config_loader import config_loader
from src.session.session_manager import get_model, get_session, set_model

logger = logging.getLogger(__name__)


@register_command("/model")
async def model_handler(session: Any, message: Dict[str, Any], args: List[str]) -> None:
    """
    /model [<name>|<index>]
    • No args: show detailed info about current model
    • <index>: switch to model by position in /models
    • <name>: switch to model by exact model name
    """
    cfg = config_loader()
    bot_name = session.client.bot_name

    # Bot-default settings
    bot_conf = cfg["telegram"][bot_name]["default"]
    bot_default_service = bot_conf["service"]
    bot_default_model = bot_conf["model"]

    # Determine active service
    state = get_session(session.chat_id)
    svc = state.active_service or bot_default_service

    # Load available models map
    models_map: Dict[str, Dict] = cfg.get("models_info", {}).get(svc, {})

    # Helper to display info for a target_model
    def format_model_info(target_model: str, info: Dict[str, Any]) -> List[str]:
        release_year = info.get("release_year", "N/A")
        creator = info.get("creator", "N/A")
        token_win = info.get("token_win", [])
        token_str = f"{token_win[0]}-{token_win[1]}" if len(token_win) == 2 else "N/A"
        rank_power = info.get("rank_power", "N/A")
        rank_coding = info.get("rank_coding", "N/A")
        rank_jail = info.get("rank_jail", "N/A")
        purpose = info.get("main_purpose", info.get("short", "N/A"))
        strengths = info.get("strengths", "N/A")
        weaknesses = info.get("weaknesses", "N/A")
        details = info.get("details", "N/A")
        jailbreaks = info.get("jailbreaks", [])

        lines = [
            f"*{target_model}*",
            f"by {creator} ({release_year})\n",
            f"*{token_str}* tokens for {purpose}\n",
            f"*Power:* {rank_power}",
            f"*Coding:* {rank_coding}",
            f"*Jailbreak:* {rank_jail}\n",
            f"+ {strengths}",
            f"- {weaknesses}\n",
            f"{details}",
        ]
        if jailbreaks:
            lines.append("*Known jailbreaks:* " + ", ".join(jailbreaks))
        return lines

    # 1) No args: show current model info
    if not args:
        current = get_model(session.chat_id) or bot_default_model
        info = models_map.get(current)
        if not info:
            await session.send_message(f"⚠️ No metadata found for model '{current}'")
            return
        lines = format_model_info(current, info)
        await session.send_message("\n".join(lines))
        return

    # 2) Arg provided: decide new_model first
    choice = args[0]
    new_model: str
    names = list(models_map.keys())

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(names):
            new_model = names[idx]
        else:
            await session.send_message(f"⚠️ Model index out of range: {choice}")
            return
    else:
        if choice in names:
            new_model = choice
        else:
            await session.send_message(
                f"⚠️ Model not found: {choice}\nUse /models to list available models."
            )
            return


    # 3) Commit and show new info
    set_model(session.chat_id, new_model)
    info = models_map.get(new_model)
    if not info:
        await session.send_message(f"⚠️ No metadata found for model '{new_model}'")
        return
    lines = ["🔄 Switched to\n"] + format_model_info(new_model, info)
    await session.send_message("\n".join(lines))
