# tests/unit/test_config_loader.py

import pytest
from llm_telegram_bot.config.config_loader import load_config
from pydantic import ValidationError


def test_load_valid_config():
    # Assumes config/config.yaml is present and valid
    cfg = load_config("config/config.yaml")
    # spot-check a few fields
    assert "groq" in cfg.services
    assert cfg.telegram.download_path == "tmp"
    assert hasattr(cfg, "models_info")
    # check one of the bots was loaded
    bot_keys = list(cfg.telegram.bots.keys())
    assert bot_keys, "No bots found in config"


def test_load_invalid_path():
    with pytest.raises(FileNotFoundError):
        load_config("does_not_exist.yaml")


def test_missing_required_field(tmp_path, monkeypatch):
    # Write a minimal broken config
    broken = tmp_path / "bad.yaml"
    broken.write_text("services: {}")  # no telegram or factorydefault
    with pytest.raises(ValidationError):
        load_config(str(broken))
