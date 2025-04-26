# File: src/commands/handlers/status.py

import logging
from typing import Any, Dict, List

from src.commands.commands_registry import register_command

logger = logging.getLogger(__name__)


# @register_command("/status")
# async def status_handler(
#     session: Any, message: Dict[str, Any], args: List[str]
# ) -> None:
#     """
#     /status
#     Check current session status: service, model, temperature, tokens, paused state.
#     """
#     cfg = config_loader()
#     chat_id = session.chat_id
#     state = get_session(chat_id)
#     bot_name = session.client.bot_name
#     bot_conf = cfg["telegram"][bot_name]["default"]

#     service = state.active_service or bot_conf.get("service")
#     model = state.active_model or bot_conf.get("model")
#     temp = getattr(state, "temperature", bot_conf.get("temperature"))
#     maxt = getattr(state, "maxtoken", bot_conf.get("maxtoken"))
#     paused = is_paused(chat_id)

#     lines = [
#         f"*Service:* {service}",
#         f"*Model:* {model}",
#         f"*Temperature:* {temp}",
#         f"*Max tokens:* {maxt}",
#         f"*Paused:* {'Yes' if paused else 'No'}",
#     ]
#     await session.send_message("\n".join(lines))

from src.session import session_manager


@register_command("/status")
async def status_handler(
    session: Any, message: Dict[str, Any], args: List[str]
) -> None:
    sess = session_manager.get_session(session.chat_id)
    model_cfg = sess.model_config

    reply = (
        f"**Service**: {sess.active_service}\n"
        f"Model: {model_cfg.model_name}\n"
        f"Temperature: {model_cfg.temperature}\n"
        f"Max tokens: {model_cfg.max_tokens}\n"
        f"Paused: {'Yes' if sess.messaging_paused else 'No'}\n"
        f"(sent as code snippet)"
    )
    await session.send_message(f"```\n{reply}\n```")
