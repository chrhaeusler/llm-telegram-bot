# tests/unit/test_routing.py
# run via "pytest tests/unit/test_routing.py"
import asyncio


def test_route_help(monkeypatch):
    # Import here so conftest sets up sys.path
    from src.commands.commands_loader import CommandInfo
    from src.telegram.routing import route_message

    # Prepare a fake commands loader

    fake_commands = {
        "help": CommandInfo(
            name="help", usage="/help", description="Show help", args_schema=[]
        )
    }

    # Monkeypatch the loader and formatter
    monkeypatch.setattr(
        "src.commands.commands_loader.load_commands_yaml", lambda: fake_commands
    )
    monkeypatch.setattr(
        "src.commands.commands_loader.format_help_text",
        lambda cmds: "Available commands:\n/help - Show help",
    )

    # Ensure help handler is registered by importing it
    from src.commands.handlers.help import help_handler  # noqa: F401

    # Dummy session
    class DummySession:
        def __init__(self):
            self.sent = []
            self.chat_id = None

        async def send_message(self, text):
            self.sent.append(text)

    session = DummySession()
    message = {"text": "/help", "chat": {"id": 42}}

    # Run route_message via asyncio
    asyncio.run(
        route_message(
            session=session,
            message=message,
            llm_call=lambda *args: asyncio.sleep(0, result=""),
            model="",
            temperature=0.0,
            maxtoken=0,
        )
    )

    # Assert that help text was sent
    assert len(session.sent) == 1
    assert session.sent[0].startswith("Available commands:")
    assert "/help - Show help" in session.sent[0]
