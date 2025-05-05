# src/llm-telegram-bot/utils/message_utils.py

import datetime
import logging
from typing import Union

from llm_telegram_bot.config.config_loader import load_jailbreaks
from llm_telegram_bot.templates.jinja import render_template

logger = logging.getLogger(__name__)


def iso_ts() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


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


# Fallback implementation — you can improve this later
def summarize_history(history: list[dict]) -> str:
    lines = [f"{entry['who']}: {entry['text']}" for entry in history if 'who' in entry and 'text' in entry]
    return "\n".join(lines[-5:]) if lines else "No summary available."


def build_full_prompt(
    char: dict,
    user: dict,
    jailbreak: Union[int, str, bool],
    history: list[dict],
    user_text: str,
    *,
    system_enabled: bool = True,
    summary_enabled: bool = True,
) -> str:

    # 1. Load & render jailbreak prompt (any Jinja errors get caught & skipped)
    rendered_jb = ""
    if isinstance(jailbreak, str):
        jb = load_jailbreaks().get(jailbreak, {})
        prompt_tpl = jb.get("prompt", "").strip()
        if prompt_tpl:
            try:
                # only attempt render if we actually have dicts
                if isinstance(char, dict) and isinstance(user, dict):
                    rendered_jb = render_template(prompt_tpl, char=char, user=user)
            except Exception as e:
                logger.warning(f"[Prompt] Skipping jailbreak render: {e}")
                rendered_jb = ""

    # 2. Optional blocks
    full_prompt = ""

    if system_enabled and rendered_jb.strip():
        # full_prompt += f"[SYSTEM]\n{rendered_jb}\n\n"
        full_prompt += f"{rendered_jb}\n\n"
    if summary_enabled:
        summary = "No summary available."  # TODO: Replace with real summary
        full_prompt += f"[SUMMARY]\n{summary}\n\n"

    # 3. Main user prompt
    full_prompt += f"[PROMPT]\n{user_text}"

    return full_prompt
