# src/llm_telegram_bot/utils/token_utils.py

import re

import tiktoken


def count_tokens_simple(text: str) -> int:
    # very rough: split on whitespace + punctuation
    return len(re.findall(r"\w+|[^\s\w]", text))

def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))