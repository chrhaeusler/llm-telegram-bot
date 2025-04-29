# tests/unit/test_routing.py

import pytest
import importlib
import pkgutil

from src.commands.commands_registry import clear_registry
from src.telegram.routing import route_message

# ------------------------------------------------------------------
# Helpers to import all handler modules so @register_command runs
# ------------------------------------------------------------------
import src.commands.handlers  # ensures the handlers package is loaded


def import_all_handlers():
    pkg = src.commands.handlers
    prefix = pkg.__name__ + "."
    for _, module_name, _ in pkgutil.iter_modules(pkg.__path__):
        importlib.import_module(f"{prefix}{module_name}")


# --------------------------------------------------
# Fixture: reset the registry around each test
# --------------------------------------------------
@pytest.fixture(autouse=True)
def reset_registry():
    clear_registry()
    yield
    clear_registry()


# --------------------------------------------------
# DummySession to capture sent messages
# --------------------------------------------------
class DummySession:
    def __init__(self):
        self.sent = []
        self.chat_id = 42

    async def send_message(self, text: str):
        self.sent.append(text)


# --------------------------------------------------
# Tests
# --------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_slash_command():
    session = DummySession()
    msg = {"text": "/nope", "chat": {"id": 42}}
    await route_message(
        session=session,
        message=msg,
        llm_call=None,
        model="M",
        temperature=0.0,
        maxtoken=0,
    )
    assert session.sent == ["⚠️ Unknown command: /nope\nSend /help for a list."]


@pytest.mark.asyncio
async def test_free_text_invokes_llm(monkeypatch):
    session = DummySession()
    called = {}

    # Stub get_session: no pause, active_service="dummy"
    class S:
        active_service = "dummy"
        messaging_paused = False

    monkeypatch.setattr('src.session.session_manager.get_session', lambda cid: S())
    # Stub config_loader: dummy service has model "M0"
    monkeypatch.setattr('src.config_loader.config_loader', lambda: {'services': {'dummy': {'model': 'M0'}}})

    async def fake_llm(text, model, temp, mt):
        called['args'] = (text, model, temp, mt)
        return "pong"

    msg = {"text": "hello", "chat": {"id": 42}}
    await route_message(
        session=session,
        message=msg,
        llm_call=fake_llm,
        model="IGNORED",
        temperature=0.2,
        maxtoken=123,
    )

    assert called['args'] == ("hello", "M0", 0.2, 123)
    assert session.sent == ["pong"]


@pytest.mark.asyncio
async def test_pause_blocks_free_text(monkeypatch):
    session = DummySession()
    session.chat_id = 99

    # Stub get_session: paused for chat 99
    class S2:
        active_service = None
        messaging_paused = True

    monkeypatch.setattr('src.session.session_manager.get_session', lambda cid: S2())

    called = False

    async def fake_llm(*args):
        nonlocal called
        called = True
        return "nope"

    msg = {"text": "anything", "chat": {"id": 99}}
    await route_message(
        session=session,
        message=msg,
        llm_call=fake_llm,
        model="X",
        temperature=0.0,
        maxtoken=0,
    )
    assert not called
    assert session.sent == []
