# src/session/session_manager.py

import asyncio
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.config.persona_loader import load_char_config, load_user_config
from llm_telegram_bot.config.schemas import BotDefaults, RootConfig, ServiceConfig
from llm_telegram_bot.utils.logger import logger


# ────────────────────────────────────────────────────
class ModelConfig:
    def __init__(self):
        self.model_name: Optional[str] = None
        self.temperature: float = 0.7
        self.max_tokens: int = 4096


class Session:
    def __init__(self, chat_id: int, bot_name: str):
        self.chat_id: int = chat_id
        self.bot_name: str = bot_name
        self.active_bot: Optional[str] = None
        self.messaging_paused: bool = False

        # Service & Model
        self.active_service: Optional[str] = None
        self.active_model: Optional[str] = None
        self.model_config: ModelConfig = ModelConfig()

        # Char, Scenario, User
        self.active_char: Optional[str] = None
        self.active_scenario: Optional[str] = None
        self.active_user: Optional[str] = None

        # Cached config data
        self.active_char_data: Optional[dict] = None
        self.active_user_data: Optional[dict] = None

        # History: TO DO: take bot configuration, if existing
        self.history_on: bool = False
        self.history_buffer: list[dict] = []

        # Jailbreak
        self.jailbreak: Optional[int] = None  # or bool if you switched to that

        # Memory
        self.memory: Dict[str, List[Any]] = {}

        # start periodic flush in background
        # (we must be running inside an asyncio loop)
        self._flush_task = asyncio.create_task(self._periodic_flush())

    def pause(self) -> None:
        self.messaging_paused = True

    def resume(self) -> None:
        self.messaging_paused = False

    async def _periodic_flush(self):
        """
        Background task to flush history every 10 minutes.
        """
        while True:
            await asyncio.sleep(600)  # 10 minutes
            try:
                if self.history_on and self.history_buffer:
                    self.flush_history_to_disk()
            except Exception as e:
                logger.exception(f"[Session {self.chat_id}] Periodic flush failed: {e}")

    def flush_history_to_disk(self) -> None:
        """
        Write self.history_buffer out to a timestamped JSON file
        under histories/<bot_name>/<chat_id>/ and then clear the buffer.
        """
        history_dir = Path("histories") / self.bot_name / str(self.chat_id)
        history_dir.mkdir(parents=True, exist_ok=True)

        history_file = history_dir / f"{self.active_user}_with_{self.active_char}.json"

        existing_data = {}
        if history_file.exists():
            with history_file.open("r", encoding="utf-8") as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = {}

        # Merge existing history
        old_history = existing_data.get("history_buffer", [])
        merged_history = old_history + self.history_buffer

        data = {
            "active_service": self.active_service,
            "active_model": self.active_model,
            "active_char": self.active_char,
            "active_user": self.active_user,
            "jailbreak": self.jailbreak,
            "history_on": self.history_on,
            "history_buffer": merged_history,
        }

        try:
            with history_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                logger.debug(f"[Session {self.chat_id}] History flushed to {history_file}")

        except Exception as e:
            logger.exception(f"[Session {self.chat_id}] Error flushing history: {e}")

        # clear in-memory buffe
        self.history_buffer.clear()

        def close(self):
            """
            Cancel background tasks (if you tear down sessions).
            """
            if hasattr(self, "_flush_task"):
                self._flush_task.cancel()


# ────────────────────────────────────────────────────
_sessions: Dict[str, Session] = {}


@lru_cache(maxsize=1)
def get_config() -> RootConfig:
    """
    Return cached RootConfig. Only loads once.
    """
    return load_config()


def get_session(chat_id: int, bot_name: str) -> Session:
    """
    Retrieve an existing Session or create a new one based on both chat_id and bot_name.
    """
    session_key = f"{chat_id}:{bot_name}"

    if session_key not in _sessions:
        session = Session(chat_id, bot_name)

        cfg: RootConfig = get_config()
        telegram_cfg = cfg.telegram
        bot_conf = telegram_cfg.bots.get(bot_name)

        if bot_conf and bot_conf.chat_id == chat_id:
            # seed LLM defaults
            session.active_service = bot_conf.default.service
            session.active_model = bot_conf.default.model

            # seed history toggle & jailbreak
            session.history_on = bot_conf.history_enabled
            session.jailbreak = bot_conf.jailbreak

            # seed persona & user keys
            session.active_char = bot_conf.char
            session.active_user = bot_conf.user

            # now load their full configs once
            if session.active_char:
                session.active_char_data = load_char_config(session.active_char, None)
            else:
                session.active_char_data = None

            if session.active_user:
                session.active_user_data = load_user_config(session.active_user, session.active_char_data)
            else:
                session.active_user_data = None

        _sessions[session_key] = session

    return _sessions[session_key]


def is_paused(chat_id: int, bot_name: str) -> bool:
    return get_session(chat_id, bot_name).messaging_paused


def get_model(chat_id: int, bot_name: str) -> Optional[str]:
    model = get_session(chat_id, bot_name).active_model
    logger.debug(f"[get_model] Active model for chat {chat_id} (bot {bot_name}): {model}")
    return model


def set_model(chat_id: int, bot_name: str, model: str) -> None:
    get_session(chat_id, bot_name).active_model = model


def get_service(chat_id: int, bot_name: str) -> Optional[str]:
    return get_session(chat_id, bot_name).active_service


def set_service(chat_id: int, bot_name: str, service: str) -> None:
    get_session(chat_id, bot_name).active_service = service


def get_temperature(chat_id: int, bot_name: str) -> float:
    return get_session(chat_id, bot_name).model_config.temperature


def set_temperature(chat_id: int, bot_name: str, temperature: float) -> None:
    get_session(chat_id, bot_name).model_config.temperature = temperature


def get_max_tokens(chat_id: int, bot_name: str) -> int:
    return get_session(chat_id, bot_name).model_config.max_tokens


def set_max_tokens(chat_id: int, bot_name: str, max_tokens: int) -> None:
    get_session(chat_id, bot_name).model_config.max_tokens = max_tokens


def get_effective_llm_params(
    chat_id: int,
    bot_name: str,
    bot_default: BotDefaults,
    svc_conf: ServiceConfig,
) -> tuple[str, float, int]:
    """
    Determine the model, temperature, and max_tokens for the given chat session.
    Priority:
        1. Per-session overrides (model_config)
        2. Active session model
        3. If bot default service is active: use bot default
        4. Else: use service config
        5. Fallback to bot default
    """
    sess = get_session(chat_id, bot_name)

    # --- Model ---
    if sess.model_config.model_name:
        model = sess.model_config.model_name
    elif sess.active_model:
        model = sess.active_model
    elif sess.active_service == bot_default.service:
        model = bot_default.model
    else:
        model = svc_conf.model or bot_default.model

    # --- Temperature ---
    if sess.model_config.temperature is not None:
        temperature = sess.model_config.temperature
    elif sess.active_service == bot_default.service:
        temperature = bot_default.temperature
    elif svc_conf.temperature is not None:
        temperature = svc_conf.temperature
    else:
        temperature = bot_default.temperature

    # --- Max tokens ---
    if sess.model_config.max_tokens is not None:
        max_toks = sess.model_config.max_tokens
    elif sess.active_service == bot_default.service:
        max_toks = bot_default.maxtoken
    elif svc_conf.maxtoken is not None:
        max_toks = svc_conf.maxtoken
    else:
        max_toks = bot_default.maxtoken

    return model, temperature, max_toks


# ────────────────────────────────────────────────────
# Chat Management
def pause(chat_id: int, bot_name: str) -> None:
    get_session(chat_id, bot_name).pause()


def resume(chat_id: int, bot_name: str) -> None:
    get_session(chat_id, bot_name).resume()


# Bot Management
def get_available_bots() -> List[str]:
    """Return a list of all configured bot names."""
    cfg = load_config()  # RootConfig
    return list(cfg.telegram.bots.keys())


def set_active_bot(chat_id: int, bot_name: str) -> None:
    get_session(chat_id, bot_name).active_bot = bot_name


def get_active_bot(chat_id: int, bot_name: str) -> Optional[str]:
    session = get_session(chat_id, bot_name)
    if session.active_bot:
        return session.active_bot
    bots = get_available_bots()
    if bots:
        session.active_bot = bots[0]
        return session.active_bot
    return None


# Character Management
def set_active_char(chat_id: int, bot_name: str, char_key: Optional[str]) -> None:
    """
    Set or clear (if None) the active character for this chat+bot,
    and immediately reload its full config into session.active_char_data.
    """
    sess = get_session(chat_id, bot_name)
    sess.active_char = char_key
    if char_key:
        # reload full char config (pass along current user_data for rendering)
        sess.active_char_data = load_char_config(char_key, sess.active_user_data)
    else:
        sess.active_char_data = None


def get_active_char(chat_id: int, bot_name: str) -> Optional[str]:
    """
    Return the active character key, or None if not set.
    """
    return get_session(chat_id, bot_name).active_char


# User Management (new)
def set_active_user(chat_id: int, bot_name: str, user_key: Optional[str]) -> None:
    """
    Set or clear (if None) the active user for this chat+bot,
    and immediately reload its full config into session.active_user_data.
    """
    sess = get_session(chat_id, bot_name)
    sess.active_user = user_key
    if user_key:
        sess.active_user_data = load_user_config(user_key, sess.active_char_data)
    else:
        sess.active_user_data = None


def get_active_user(chat_id: int, bot_name: str) -> Optional[str]:
    """
    Return the active user key, or None if not set.
    """
    return get_session(chat_id, bot_name).active_user


# Scenario Management
def set_active_scenario(chat_id: int, bot_name: str, scenario_key: str) -> None:
    get_session(chat_id, bot_name).active_scenario = scenario_key


def get_active_scenario(chat_id: int, bot_name: str) -> Optional[str]:
    return get_session(chat_id, bot_name).active_scenario


# Memory Management
def get_memory(chat_id: int, bot_name: str) -> Dict[str, List[Any]]:
    return get_session(chat_id, bot_name).memory


def add_memory(chat_id: int, bot_name: str, bucket: str, value: Any) -> None:
    session = get_session(chat_id, bot_name)
    session.memory.setdefault(bucket, []).append(value)
