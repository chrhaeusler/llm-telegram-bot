"""
lets us load the command descriptions from commands.yaml and fetch usage/help info for individual commands. This will plug into routing and help logic soon.
"""

# src/commands/commands_loader.py

import html
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
    with _COMMANDS_FILE.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    commands: dict[str, CommandInfo] = {}
    for name, entry in raw.items():
        usage = entry.get("usage", f"/{name}")
        description = entry.get("description", "")
        commands[name] = CommandInfo(name, usage, description)

    return commands


def format_help_text(commands: dict[str, CommandInfo]) -> str:
    """
    Formats a readable help message for the /help command in HTML.
    Wraps command usage in <code>…</code> and escapes all <, >, &.
    """
    lines: list[str] = []
    # Header
    lines.append("<b>Available commands:</b>")
    lines.append("")

    for name, cmd in sorted(commands.items()):
        # Escape any HTML-sensitive chars
        safe_usage = html.escape(cmd.usage)
        safe_desc = html.escape(cmd.description)
        # Show usage in monospace, then description
        lines.append(f"<code>{safe_usage}</code> — {safe_desc}")
        lines.append("")

    # remove trailing blank
    if lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)
