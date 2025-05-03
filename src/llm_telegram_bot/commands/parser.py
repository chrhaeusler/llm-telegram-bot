# src/commands/parser.py

from typing import Any, List

from llm_telegram_bot.commands.commands_loader import CommandInfo


class ArgParseError(Exception):
    pass


class ParsedCommand:
    def __init__(
        self,
        name: str,
        raw_args: str,
        parsed_args: dict[str, Any],
    ):
        self.name = name
        self.raw_args = raw_args
        self.parsed_args = parsed_args

    def __repr__(self):
        return f"<ParsedCommand name={self.name} parsed_args={self.parsed_args}>"


def parse_command(text: str, info: CommandInfo) -> ParsedCommand:
    """
    Parse a command string like "/foo --bar 123 baz" into a ParsedCommand,
    validating against info.args_schema.
    """
    parts = text.strip().split()
    if not parts:
        raise ArgParseError("Empty input")

    cmd = parts[0].lstrip("/")
    raw_args = " ".join(parts[1:])

    # We expect info.args_schema to be a list of ArgSpec objects, not dicts.
    # error: "CommandInfo" has no attribute "args_schema"
    schema: List[ArgSpec] = info.args_schema or []
    result: dict[str, Any] = {}
    remaining: List[str] = parts[1:]

    for arg_def in schema:
        name = arg_def.name  # Access attribute directly
        typ = arg_def.type if arg_def.type else "str"  # Access attribute directly
        optional = arg_def.optional  # Access attribute directly
        flag = arg_def.flag  # Access attribute directly

        if flag:
            # Flag like --ask
            if flag in remaining:
                result[name] = True
                remaining.remove(flag)
            else:
                result[name] = False
        else:
            if remaining:
                val = remaining.pop(0)
                if typ == "int":
                    try:
                        result[name] = int(val)
                    except ValueError:
                        raise ArgParseError(f"Expected integer for '{name}', got '{val}'")
                elif typ == "float":
                    try:
                        result[name] = float(val)
                    except ValueError:
                        raise ArgParseError(f"Expected float for '{name}', got '{val}'")
                else:
                    result[name] = val
            elif optional:
                result[name] = None
            else:
                raise ArgParseError(f"Missing required argument: {name}")

    return ParsedCommand(cmd, raw_args, result)
