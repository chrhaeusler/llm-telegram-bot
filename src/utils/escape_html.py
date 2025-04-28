# src/utils/escape_html.py


def html_escape(text: str) -> str:
    """
    Escape only the < and > characters so that
    Telegram’s HTML parser sees your tags but
    any user‐supplied angle‐brackets are neutralized.
    """
    # First strip any stray MarkdownV2 backslashes
    import re

    text = re.sub(
        r'\\([!"#$%&\'()*+,\-./:;<=>?@\[\\\]^_`{|}~])',
        r"\1",
        text,
    )
    # Now escape only < and >:
    return text.replace("<", "&lt;").replace(">", "&gt;")
