"""
lets us load the command descriptions from commands.yaml and fetch usage/help info for individual commands. This will plug into routing and help logic soon.
"""

# src/commands/commands_loader.py

from pathlib import Path

import yaml

_COMMANDS_FILE = Path("config/commands.yaml")


class CommandInfo:
    def __init__(self, name: str, usage: str, description: str):
        self.name = name
        self.usage = usage
        self.description = description

    def __repr__(self):
        return f"<CommandInfo name={self.name}>"


def load_commands_yaml() -> dict[str, CommandInfo]:
    """Loads commands from config/commands.yaml and returns a dict of CommandInfo by command name."""
    with _COMMANDS_FILE.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    commands = {}
    for name, entry in raw.items():
        usage = entry.get("usage", f"/{name}")
        description = entry.get("description", "")
        commands[name] = CommandInfo(name, usage, description)

    return commands


def format_help_text(commands: dict[str, CommandInfo]) -> str:
    """Formats a readable help message for the /help command."""
    lines = ["Available commands:"]
    for name, cmd in sorted(commands.items()):
        lines.append(f"{cmd.usage:<20} - {cmd.description}")
    return "\n".join(lines)
