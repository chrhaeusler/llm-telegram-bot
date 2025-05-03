# src/llm-telegram-bot/utils/message_utils.py

def split_message(text: str, limit: int = 4096) -> list[str]:
    """
    Splits a long message into chunks suitable for Telegram (max 4096 chars).
    Attempts to split at paragraph or sentence boundaries if possible.
    """
    chunks = []
    while len(text) > limit:
        # Try to split at the last newline before limit
        split_index = text.rfind("\n", 0, limit)
        if split_index == -1:
            # Try to split at the last space
            split_index = text.rfind(" ", 0, limit)
        if split_index == -1:
            split_index = limit  # hard cut

        chunks.append(text[:split_index].strip())
        text = text[split_index:].strip()

    if text:
        chunks.append(text)
    return chunks