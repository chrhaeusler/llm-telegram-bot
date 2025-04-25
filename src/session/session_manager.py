# src/session/session_manager.py
"""
Session manager for per-chat sessions, handling paused state, active char/scenario, and memory buckets.
"""
from typing import Dict, Any, Optional


class Session:
    """
    Represents a session for a single chat_id.
    """
    def __init__(self, chat_id: int):
        self.chat_id: int = chat_id
        self.messaging_paused: bool = False
        self.active_char: Optional[str] = None
        self.active_scenario: Optional[str] = None
        self.memory: Dict[str, list[Any]] = {}

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

    Args:
        chat_id (int): Telegram chat identifier.

    Returns:
        Session: The session object for the given chat_id.
    """
    if chat_id not in _sessions:
        _sessions[chat_id] = Session(chat_id)
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


def set_active_char(chat_id: int, char_key: str) -> None:
    """Set the active character for the session."""
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


def get_memory(chat_id: int) -> Dict[str, list[Any]]:
    """Return the memory buckets for the session."""
    return get_session(chat_id).memory


def add_memory(chat_id: int, bucket: str, value: Any) -> None:
    """Add a value to a named memory bucket for the session."""
    session = get_session(chat_id)
    session.memory.setdefault(bucket, []).append(value)
