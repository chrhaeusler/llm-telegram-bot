# tests/unit/test_models_info_schema.py

import json
import pytest
from llm_telegram_bot.config.schemas import ModelInfo, RootConfig

# A minimal stub for required RootConfig fields, excluding telegram/services
_BASE_CFG = {
    "services": {},
    "telegram": {
        "download_path": "tmp",
        "chat_history_path": "tmp",
        "polling_active_period": 1,
        "polling_interval_active": 1,
        "polling_interval_idle": 1,
        # no bot_* entries here; TelegramConfig will error if you try to parse RootConfig fully.
        # We’ll only validate models_info in isolation via ModelInfo.
    },
    "factorydefault": {
        "command_prefix": "/",
        "logging_enabled": True,
        "history_enabled": True,
        "history_file": "h.log",
        "service": "groq",
        "model": "x",
        "temperature": 0.5,
        "maxtoken": 1024,
        "top_p": 0.9,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
    },
}


def test_model_info_parsing():
    raw = {
        "creator": "Groq",
        "short": "Compact version of Groq’s beta model.",
        "release_year": "2024",
        "token_win": [2048, 4096],
        "strengths": "Lightweight model.",
        "weaknesses": "Limited capacity.",
        "rank_power": "low",
        "rank_coding": "low",
        "rank_jail": "high",
        "jailbreaks": ["prompt injection"],
        "details": "tailored for low resources.",
        "main_purpose": "general-purpose text generation",
    }
    mi = ModelInfo.model_validate(raw)
    assert mi.creator == "Groq"
    assert mi.token_win == [2048, 4096]
    assert isinstance(mi.jailbreaks, list)


def test_models_info_in_rootconfig():
    # Insert our minimal model info under models_info
    model_info = {
        "groq": {
            "compound-beta-mini": {
                "creator": "Groq",
                "short": "Compact version...",
                "release_year": "2024",
                "token_win": [2048, 4096],
                "strengths": "Lightweight...",
                "weaknesses": "Limited capacity...",
                "rank_power": "low",
                "rank_coding": "low",
                "rank_jail": "high",
                "jailbreaks": ["injection"],
                "details": "details",
                "main_purpose": "gen",
            }
        }
    }

    cfg_dict = {**_BASE_CFG, "models_info": model_info}
    # This should parse without raising
    RootConfig.model_validate(cfg_dict)
