# src/utils/markdown.py

import re

_escape_chars = r"_*[]()~`>#+-=|{}.!<>"


def escape_markdown(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2 formatting.
    """
    return re.sub(rf"([{re.escape(_escape_chars)}])", r"\\\1", text)


def safe_message(text: str) -> str:
    """
    Prepares a message to send safely by escaping MarkdownV2 characters.
    """
    return escape_markdown(text)
