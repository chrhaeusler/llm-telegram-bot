# src/llm_telegram_bot/types/character.py (example)
from typing import TypedDict


class CharacterDict(TypedDict):
    name: str
    role: str


class UserDict(TypedDict):
    name: str
    role: str