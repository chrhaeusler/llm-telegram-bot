# src/llm_telegram_bot/commands/handlers/model.py

from typing import Any, Dict, List

from llm_telegram_bot.commands.commands_registry import register_command
from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.config.schemas import BotConfig, ModelInfo
from llm_telegram_bot.session.session_manager import (
    get_model,
    get_session,
    set_model,
)
from llm_telegram_bot.utils.logger import logger

logger.info("[Model Handler] model.py is being loaded")


@register_command("/model")
async def model_handler(session: Any, message: dict, args: List[str]) -> None:
    """
    /model [<name>|<index>]
    • No args: Show detailed info about the current model
    • <index>: Switch to model by position in /models
    • <name>: Switch to model by exact model name
    """
    # Load typed config
    cfg = load_config()  # RootConfig
    tg_cfg = cfg.telegram  # TelegramConfig

    bot_name = session.client.bot_name
    bot_conf: BotConfig | None = tg_cfg.bots.get(bot_name)
    if not bot_conf:
        await session.send_message("❌ Bot configuration not found.")
        return

    default_conf = bot_conf.default  # BotDefaults

    # Determine active service
    sess = get_session(session.chat_id, session.bot_name)
    svc = sess.active_service or default_conf.service

    # Load available models map
    models_map: Dict[str, ModelInfo] = cfg.models_info.get(svc, {})

    def format_model_info(target_model: str, info: ModelInfo) -> List[str]:
        token_win = info.token_win
        token_str = f"{token_win[0]}-{token_win[1]}" if len(token_win) == 2 else "N/A"
        lines = [
            f"<b>{target_model}</b>",
            f"by {info.creator} ({info.release_year})\n",
            f"<b>{token_str}</b> tokens for {info.main_purpose or info.short}\n",
            f"<b>Power:</b> {info.rank_power}",
            f"<b>Coding:</b> {info.rank_coding}",
            f"<b>Jailbreak:</b> {info.rank_jail}\n",
            f"+ {info.strengths}",
            f"- {info.weaknesses}\n",
            f"<b>Details:</b> {info.details}\n",
        ]
        if info.jailbreaks:
            lines.append("<b>Jailbreaks:</b> " + ", ".join(info.jailbreaks))
        lines.append(f"\n<b>{target_model}</b> 👈")
        return lines

    # 1) No args: Show current model info
    if not args:
        current = get_model(session.chat_id, session.bot_name) or default_conf.model
        info = models_map.get(current)
        if not info:
            await session.send_message(f"⚠️ No metadata for model '{current}'")
            return
        lines = format_model_info(current, info)
        await session.send_message("\n".join(lines), parse_mode="HTML")
        return

    # 2) Arg provided: Determine new_model
    choice = args[0]
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
            await session.send_message(f"⚠️ Model not found: {choice}\nUse /models to list available models.")
            return

    # 3) Commit and show new info
    set_model(session.chat_id, session.bot_name, new_model)
    info = models_map.get(new_model)
    if not info:
        await session.send_message(f"⚠️ No metadata for model '{new_model}'")
        return
    lines = ["🔄 Switched to"] + format_model_info(new_model, info)
    await session.send_message("\n".join(lines), parse_mode="HTML")
