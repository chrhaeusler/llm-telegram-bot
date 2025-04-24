# src/commands/commands_loader.py
"""
Lets us load the command descriptions from commands.yaml and fetch usage/help info for individual commands.
This will plug into routing and help logic soon.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_COMMANDS_FILE = Path("config/commands.yaml")


@dataclass
class ArgSpec:
    name: str
    type: str = "str"  # default to string if not specified
    optional: bool = False
    flag: str | None = None


@dataclass
class CommandInfo:
    name: str
    usage: str
    description: str
    args_schema: list[ArgSpec]


def load_commands_yaml() -> dict[str, CommandInfo]:
    """Loads commands from config/commands.yaml and returns a dict of CommandInfo by command name."""
    with _COMMANDS_FILE.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    commands = {}
    for name, entry in raw.items():
        usage = entry.get("usage", f"/{name}")
        description = entry.get("description", "")

        raw_args = entry.get("args", [])
        args_schema = []
        for arg in raw_args:
            args_schema.append(
                ArgSpec(
                    name=arg["name"],
                    type=arg.get("type", "str"),
                    optional=arg.get("optional", False),
                    flag=arg.get("flag"),
                )
            )

        commands[name] = CommandInfo(
            name=name,
            usage=usage,
            description=description,
            args_schema=args_schema,
        )

    return commands


def format_help_text(commands: dict[str, CommandInfo]) -> str:
    """Formats a readable help message for the /help command, preserving YAML order and adding spacing."""
    lines: list[str] = ["Available commands:"]
    # Preserve insertion order as defined in commands.yaml
    for cmd in commands.values():
        # Clean description to remove unintended newlines
        desc = cmd.description.strip()
        # Append usage on its own line
        lines.append(cmd.usage)
        # Append each line of the description indented
        for desc_line in desc.splitlines():
            lines.append(f"{desc_line}")
        # Blank line between commands
        lines.append("")
    # Remove the last blank line for clean output
    if lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)
