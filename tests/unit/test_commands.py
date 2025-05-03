# tests/unit/test_commands.py

import importlib
import pkgutil
import pytest

from llm_telegram_bot.commands.commands_loader import load_commands_yaml
from llm_telegram_bot.commands.commands_registry import is_command_implemented

# ── Step 1: Import all handler modules so their @register_command fire ──
import llm_telegram_bot.commands.handlers  # base package


def import_all_handlers():
    pkg = importlib.import_module("src.llm_telegram_bot.commands.handlers")
    prefix = pkg.__name__ + "."
    for _finder, module_name, _ispkg in pkgutil.iter_modules(pkg.__path__):
        importlib.import_module(f"{prefix}{module_name}")


# ── Fixture: ensure handlers are loaded before assertions ──
@pytest.fixture(autouse=True)
def load_handlers():
    import_all_handlers()


def test_every_usage_registered():
    """
    For each entry in commands.yaml, grab its usage (e.g. "/foo [args]"),
    extract the "/foo" part → "foo", and assert we have a handler registered.
    """
    cmds = load_commands_yaml()
    missing = []
    for name, info in cmds.items():
        # usage is like "/foo [<bar>]". Take the first token, strip "/" & any "@bot"
        usage = info.usage.strip().split()[0]  # e.g. "/foo@MyBot"
        cmd = usage.lstrip("/").split("@", 1)[0]  # -> "foo"
        if not is_command_implemented(cmd):
            missing.append(cmd)

    if missing:
        pytest.fail(f"No handler registered for slash commands: {missing}")
