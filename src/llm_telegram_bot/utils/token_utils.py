# src/llm_telegram_bot/utils/token_utils.py

import tiktoken


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))
