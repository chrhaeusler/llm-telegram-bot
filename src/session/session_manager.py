# src/session/session_manager.py
"""
Session manager for per-chat sessions:
- paused state
- active_bot
- active_char (persona)
- active_scenario
- memory buckets
- list of available bots loaded from config
"""
from typing import Any, Dict, List, Optional

from src.config_loader import config_loader


class Session:
    """
    Represents a session for a single chat_id.
    """

    def __init__(self, chat_id: int):
        self.chat_id: int = chat_id
        # Bot control
        self.messaging_paused: bool = False
        self.active_bot: Optional[str] = None
        # Service
        self.active_service: Optional[str] = None
        # Roleplay
        self.active_char: Optional[str] = None
        self.active_scenario: Optional[str] = None
        # Dynamic memory
        self.memory: Dict[str, List[Any]] = {}

    def pause(self) -> None:
        """Pause messaging to the LLM for this session."""
        self.messaging_paused = True

    def resume(self) -> None:
        """Resume messaging to the LLM for this session."""
        self.messaging_paused = False


# Internal storage of sessions by chat_id
_sessions: Dict[int, Session] = {}


def get_session(chat_id: int) -> Session:
    """
    Retrieve an existing Session or create a new one.
    """
    if chat_id not in _sessions:
        session = Session(chat_id)

        # Set a default service from config
        from src.config_loader import config_loader

        config = config_loader()
        default_service = next(iter(config.get("services", {}).keys()), None)
        session.active_service = default_service

        _sessions[chat_id] = session

    return _sessions[chat_id]


def pause(chat_id: int) -> None:
    """Pause messaging for the given chat_id."""
    get_session(chat_id).pause()


def resume(chat_id: int) -> None:
    """Resume messaging for the given chat_id."""
    get_session(chat_id).resume()


def is_paused(chat_id: int) -> bool:
    """Check if messaging is paused for the given chat_id."""
    return get_session(chat_id).messaging_paused


# ── Bot Management ────────────────────────────────────────────────────────


def get_available_bots() -> List[str]:
    """
    Return list of bot names enabled in config.
    """
    cfg = config_loader()
    bots = []
    for name, conf in cfg.get("telegram", {}).items():
        if not isinstance(conf, dict):
            continue
        if conf.get("enabled", False):
            bots.append(name)
    return bots


def set_active_bot(chat_id: int, bot_name: str) -> None:
    """Set the active bot for the session."""
    get_session(chat_id).active_bot = bot_name


def get_active_bot(chat_id: int) -> Optional[str]:
    """Get the active bot for the session (default first available)."""
    session = get_session(chat_id)
    if session.active_bot:
        return session.active_bot
    bots = get_available_bots()
    if bots:
        session.active_bot = bots[0]
        return session.active_bot
    return None


# Then, add these functions to the module:
def get_service(chat_id: int) -> Optional[str]:
    """Get the currently selected LLM service."""
    return get_session(chat_id).active_service


def set_service(chat_id: int, service: str) -> None:
    """Set the active LLM service."""
    get_session(chat_id).active_service = service


# ── Persona (Character) Management ─────────────────────────────────────────


def set_active_char(chat_id: int, char_key: str) -> None:
    """Set the active character (persona) for the session."""
    get_session(chat_id).active_char = char_key


def get_active_char(chat_id: int) -> Optional[str]:
    """Get the active character for the session."""
    return get_session(chat_id).active_char


def set_active_scenario(chat_id: int, scenario_key: str) -> None:
    """Set the active scenario for the session."""
    get_session(chat_id).active_scenario = scenario_key


def get_active_scenario(chat_id: int) -> Optional[str]:
    """Get the active scenario for the session."""
    return get_session(chat_id).active_scenario


# ── Memory Management ──────────────────────────────────────────────────────


def get_memory(chat_id: int) -> Dict[str, List[Any]]:
    """Return the memory buckets for the session."""
    return get_session(chat_id).memory


def add_memory(chat_id: int, bucket: str, value: Any) -> None:
    """Add a value to a named memory bucket for the session."""
    session = get_session(chat_id)
    session.memory.setdefault(bucket, []).append(value)
