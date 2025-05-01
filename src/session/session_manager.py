# src/session/session_manager.py

from typing import Any, Dict, List, Optional

from src.config_loader import config_loader
from src.utils.logger import logger


# ────────────────────────────────────────────────────
class ModelConfig:
    def __init__(self):
        self.model_name: Optional[str] = None
        self.temperature: float = 0.7
        self.max_tokens: int = 4096


class Session:
    def __init__(self, chat_id: int):
        self.chat_id: int = chat_id
        self.active_bot: Optional[str] = None
        self.messaging_paused: bool = False
        self.active_service: Optional[str] = None
        self.active_model: Optional[str] = None
        self.model_config: ModelConfig = ModelConfig()
        self.active_char: Optional[str] = None
        self.active_scenario: Optional[str] = None
        self.memory: Dict[str, List[Any]] = {}

    def pause(self) -> None:
        self.messaging_paused = True

    def resume(self) -> None:
        self.messaging_paused = False


# ────────────────────────────────────────────────────
_sessions: Dict[int, Session] = {}


def get_session(chat_id: int) -> Session:
    """
    Retrieve an existing Session or create a new one.
    When newly creating, seed `active_service` and `active_model`
    from the telegram-config for whichever bot owns `chat_id`.
    """
    if chat_id not in _sessions:
        session = Session(chat_id)

        cfg = config_loader()
        # 1) Find which bot this chat_id belongs to
        bot_name = None
        for name, conf in cfg.get("telegram", {}).items():
            if isinstance(conf, dict) and conf.get("chat_id") == chat_id:
                bot_name = name
                break

        # 2) Seed active_service from first service in config
        default_service = next(iter(cfg.get("services", {}).keys()), None)
        session.active_service = default_service

        # 3) If we found a bot_name, seed its default model
        if bot_name:
            bot_conf = cfg["telegram"][bot_name].get("default", {})
            session.active_model = bot_conf.get("model")

        _sessions[chat_id] = session

    return _sessions[chat_id]


def is_paused(chat_id: int) -> bool:
    return get_session(chat_id).messaging_paused


def get_model(chat_id: int) -> Optional[str]:
    model = get_session(chat_id).active_model
    logger.debug(f"[get_model] Active model for chat {chat_id}: {model}")
    return model


def set_model(chat_id: int, model: str) -> None:
    get_session(chat_id).active_model = model


def get_service(chat_id: int) -> Optional[str]:
    return get_session(chat_id).active_service


def set_service(chat_id: int, service: str) -> None:
    get_session(chat_id).active_service = service


def get_temperature(chat_id: int) -> float:
    return get_session(chat_id).model_config.temperature


def set_temperature(chat_id: int, temperature: float) -> None:
    get_session(chat_id).model_config.temperature = temperature


def get_max_tokens(chat_id: int) -> int:
    return get_session(chat_id).model_config.max_tokens


def set_max_tokens(chat_id: int, max_tokens: int) -> None:
    get_session(chat_id).model_config.max_tokens = max_tokens


def get_effective_llm_params(
    chat_id: int,
    bot_default: Dict[str, Any],
    svc_conf: Dict[str, Any],
) -> tuple[str, float, int]:
    sess = get_session(chat_id)

    model = sess.active_model or ""
    if not model:
        if sess.active_service == bot_default.get("service"):
            model = bot_default.get("model", "")
        else:
            model = svc_conf.get("model", bot_default.get("model", ""))

    temp = sess.model_config.temperature
    if sess.active_service == bot_default.get("service"):
        temp = bot_default.get("temperature", temp)
    else:
        temp = svc_conf.get("temperature", temp)

    max_toks = sess.model_config.max_tokens
    if sess.active_service == bot_default.get("service"):
        max_toks = bot_default.get("maxtoken", max_toks)
    else:
        max_toks = svc_conf.get("maxtoken", max_toks)

    return model, float(temp), int(max_toks)


# ────────────────────────────────────────────────────
# Chat Management
def pause(chat_id: int) -> None:
    get_session(chat_id).pause()


def resume(chat_id: int) -> None:
    get_session(chat_id).resume()


# Bot Management
def get_available_bots() -> List[str]:
    cfg = config_loader()
    bots: List[str] = []
    for name, conf in cfg.get("telegram", {}).items():
        if isinstance(conf, dict) and conf.get("enabled", False):
            bots.append(name)
    return bots


def set_active_bot(chat_id: int, bot_name: str) -> None:
    get_session(chat_id).active_bot = bot_name


def get_active_bot(chat_id: int) -> Optional[str]:
    session = get_session(chat_id)
    if session.active_bot:
        return session.active_bot
    bots = get_available_bots()
    if bots:
        session.active_bot = bots[0]
        return session.active_bot
    return None


# Persona (Character) Management
def set_active_char(chat_id: int, char_key: str) -> None:
    get_session(chat_id).active_char = char_key


def get_active_char(chat_id: int) -> Optional[str]:
    return get_session(chat_id).active_char


def set_active_scenario(chat_id: int, scenario_key: str) -> None:
    get_session(chat_id).active_scenario = scenario_key


def get_active_scenario(chat_id: int) -> Optional[str]:
    return get_session(chat_id).active_scenario


# Memory Management
def get_memory(chat_id: int) -> Dict[str, List[Any]]:
    return get_session(chat_id).memory


def add_memory(chat_id: int, bucket: str, value: Any) -> None:
    session = get_session(chat_id)
    session.memory.setdefault(bucket, []).append(value)
