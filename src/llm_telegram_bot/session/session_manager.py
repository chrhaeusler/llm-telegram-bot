# src/llm_telegram_bot/session/session_manager.py

import asyncio
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.config.persona_loader import load_char_config, load_user_config
from llm_telegram_bot.config.schemas import BotDefaults, RootConfig, ServiceConfig
from llm_telegram_bot.session.history_manager import HistoryManager, Message
from llm_telegram_bot.utils.logger import logger

MAX_HISTORY_BYTES = 1_000_000

# yeah just, quickly testing
NO_MAX_MESSAGES = 25
T0_SENTENCE_CAP = 8


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

        # ── Messaging state ──────────────────────────────
        self.active_bot: Optional[str] = None
        self.messaging_paused: bool = False

        # ── Service & Model ──────────────────────────────
        self.active_service: Optional[str] = None
        self.active_model: Optional[str] = None
        self.model_config: ModelConfig = ModelConfig()

        # ── Persona & Scenario ────────────────────────────
        self.active_char: Optional[str] = None
        self.active_scenario: Optional[str] = None
        self.active_user: Optional[str] = None
        self.active_char_data: Optional[dict] = None
        self.active_user_data: Optional[dict] = None

        # ── Legacy history buffer (for `/history`) ────────
        self.history_on: bool = False
        self.history_buffer: list[dict] = []

        # ── Jailbreak toggle ──────────────────────────────
        self.jailbreak: Optional[int] = None

        # ── Ephemeral memory ──────────────────────────────
        self.memory: Dict[str, List[Any]] = {}

        # ── Tiered history manager (hard-coded for now) ───
        # TO DO: pull these values from config.yaml instead of hard-coding
        #   N0 = max raw msgs before promoting to tier1
        #   N1 = max summaries before promoting to tier2
        #   K  = how many tier1 summaries to batch into one mega
        #   T0/T1/T2_caps = token caps for each tier
        self.history_mgr = HistoryManager(
            bot_name=bot_name,
            chat_id=chat_id,
            N0=NO_MAX_MESSAGES,  # max messages to hold in this tier
            N1=22,
            K=7,
            T0_cap=T0_SENTENCE_CAP,  # max sentences of summary
            T1_cap=3,
            T2_cap=222,
        )

        # Start periodic flush every 10 minutes
        # MUST be inside a running asyncio loop
        loop = asyncio.get_event_loop()
        self._flush_task = loop.create_task(self._periodic_flush())

    def pause(self) -> None:
        self.messaging_paused = True

    def resume(self) -> None:
        self.messaging_paused = False

    async def _periodic_flush(self):
        while True:
            await asyncio.sleep(600)  # 10 minutes
            try:
                if self.history_on and self.history_buffer:
                    path = self.flush_history_to_disk()  # consumes history_buffer only
                    logger.debug(f"[Session {self.chat_id}] Periodic flush wrote to {path}")
            except Exception as e:
                logger.exception(f"[Session {self.chat_id}] Periodic flush failed: {e}")

    def flush_history_to_disk(self) -> Path:
        """
        Rotate+append: find the highest‐version file,
        bump if it’s over MAX_HISTORY_BYTES, merge, write back,
        then clear only self.history_buffer.
        """
        history_dir = Path("histories") / self.bot_name / str(self.chat_id)
        history_dir.mkdir(parents=True, exist_ok=True)

        base = f"{self.active_user}_with_{self.active_char}"
        # regex to capture an optional “_vN”
        pattern = re.compile(rf"^{re.escape(base)}(?:_v(\d+))?\.json$")

        candidates = []
        for p in history_dir.glob(f"{base}*.json"):
            m = pattern.match(p.name)
            if not m:
                continue
            ver = int(m.group(1) or 1)
            candidates.append((ver, p))
        if candidates:
            candidates.sort()
            ver, path = candidates[-1]
            # if the latest file is too big, bump version
            if path.stat().st_size >= MAX_HISTORY_BYTES:
                ver += 1
                path = history_dir / f"{base}_v{ver}.json"
        else:
            # first time ever
            ver, path = 1, history_dir / f"{base}.json"

        # load existing payload if any
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

        old = existing.get("history_buffer", [])
        merged = old + self.history_buffer

        payload = {
            "active_service": self.active_service,
            "active_model": self.active_model,
            "active_char": self.active_char,
            "active_user": self.active_user,
            "jailbreak": self.jailbreak,
            "history_on": self.history_on,
            "history_buffer": merged,
        }

        # write merged back out
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.debug(f"[Session {self.chat_id}] History flushed to {path}")

        # clear only in-memory buffer
        self.history_buffer.clear()
        return path

    def load_history_from_disk(self) -> str:
        """
        Find the highest‐version history file, load its full history_buffer,
        then seed our HistoryManager.tier0 with only the last N0*2 entries
        (so you pick up exactly the most recent N₀ user+bot exchanges).
        """
        history_dir = Path("histories") / self.bot_name / str(self.chat_id)
        if not history_dir.exists():
            raise FileNotFoundError(f"No history directory at {history_dir}")

        base = f"{self.active_user}_with_{self.active_char}"
        pattern = re.compile(rf"^{re.escape(base)}(?:_v(\d+))?\.json$")
        versions = []
        for p in history_dir.glob(f"{base}*.json"):
            m = pattern.match(p.name)
            if not m:
                continue
            ver = int(m.group(1) or 1)
            versions.append((ver, p))

        if not versions:
            raise FileNotFoundError(f"No versions of {base}*.json in {history_dir}")

        # pick the highest version
        _, latest = sorted(versions)[-1]

        # load raw payload
        data = json.loads(latest.read_text(encoding="utf-8"))
        full_buffer = data.get("history_buffer", [])
        # self.history_buffer = full_buffer  # keep full for manual flush

        logger.info(f"[Session {self.chat_id}] Loaded {len(full_buffer)} entries from {latest}")

        # seed HistoryManager with only the last N0*2 entries
        N0 = self.history_mgr.N0
        # TO DO: this should be adjusted as soon as tier-1, and tier-2 are implemented
        recent_raw = full_buffer[-(N0 * 2) :]

        for entry in recent_raw:
            msg = Message(
                ts=entry["ts"],
                who=entry["who"],
                lang=entry.get("lang", "unknown"),
                text=entry["text"],
                compressed=entry.get("compressed", entry["text"]),
                tokens_text=entry.get("tokens_text", len(entry["text"].split())),
                tokens_compressed=entry.get("tokens_compressed", entry.get("tokens_text", len(entry["text"].split()))),
            )
            # dispatch into user vs bot so your promotions work correctly
            if entry["who"] == self.active_user_data["identity"]["name"]:
                self.history_mgr.add_user_message(msg)
            else:
                self.history_mgr.add_bot_message(msg)

        return str(latest)

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

            session.history_file_template = (
                bot_conf.history_file
                or "{{user.identity.name}}_{{user.role}}_with_{{char.identity.name}}_{{char.role}}.json"
            )

            user_data = load_user_config(session.active_user, None) or {}
            session.active_char_data = load_char_config(session.active_char, user_data) or {}
            session.active_user_data = load_user_config(session.active_user, session.active_char_data) or {}

            try:
                path = session.load_history_from_disk()
                logger.info(f"[Session {chat_id}] Start-History geladen aus {path}")

                # Seed in den Manager
                from llm_telegram_bot.session.history_manager import Message

                for entry in session.history_buffer:
                    session.history_mgr.tier0.append(
                        Message(
                            ts=entry["ts"],
                            who=entry["who"],
                            lang=entry.get("lang", "unknown"),
                            text=entry["text"],
                            compressed=entry.get("compressed", entry["text"]),
                            tokens_text=entry.get("tokens_text", 0),
                            tokens_compressed=entry.get("tokens_compressed", entry.get("tokens_text", 0)),
                        )
                    )

                    # ---- NEW: drop loaded entries so they don’t get re-flushed ----
                    session.history_buffer.clear()

                logger.info(
                    f"[Session {session.chat_id}] Loaded " f"{len(session.history_buffer)} history entries on startup"
                )
            except FileNotFoundError:
                # no prior history file, start fresh
                pass

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
        user_data = sess.active_user_data or {}
        sess.active_char_data = load_char_config(char_key, user_data) or {}
    else:
        sess.active_char_data = {}


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
        sess.active_user_data = load_user_config(user_key, sess.active_char_data) or {}
    else:
        sess.active_user_data = {}


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
