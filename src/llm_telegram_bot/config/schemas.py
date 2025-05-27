# src/config/schemas.py

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ServiceConfig(BaseModel):
    enabled: bool
    endpoint: str
    api_key: str
    model: str
    timeout: int = Field(..., gt=0, description="Request timeout in seconds")
    retries: int = Field(..., ge=0, description="Number of retry attempts on failure")
    model_params: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional additional parameters for model invocation",
    )


class BotDefaults(BaseModel):
    service: str
    model: str
    show_think_blocks: bool = True
    temperature: float = Field(..., ge=0.0, le=2.0)
    maxtoken: int = Field(..., gt=0)
    top_p: float = Field(..., ge=0.0, le=1.0)
    frequency_penalty: float = Field(..., description="Penalty for frequent tokens")
    presence_penalty: float = Field(..., description="Penalty for previously mentioned tokens")


class BotConfig(BaseModel):
    enabled: bool
    name: str
    handle: str
    token: str
    chat_id: int

    polling_active_period: int = Field(..., gt=0)
    polling_interval_active: int = Field(..., gt=0)
    polling_interval_idle: int = Field(..., gt=0)

    download_path: Optional[str] = Field(None, description="Base path for file downloads")
    chat_history_path: Optional[str] = Field(None, description="Base path for chat history files")

    char: str = Field(..., description="Default character YAML name")
    user: str = Field(..., description="Default user YAML name")

    command_prefix: str = Field(..., min_length=1)
    logging_enabled: bool
    history_enabled: bool
    history_flush_count: int = Field(
        default=10, gt=0, description="Number of messages to buffer before flushing to disk"
    )
    jailbreak: Optional[str] = Field(
        default=None, description="Key of standard jailbreak prompt to insert from jailbreaks.yaml (false = off)"
    )
    history_file: str = Field(
        ..., description="Filename template for history JSON, supports {{user.name}}, {{char.name}} etc."
    )

    default: BotDefaults


class TelegramConfig(BaseModel):
    download_path: str
    chat_history_path: str
    polling_active_period: int = Field(..., gt=0)
    polling_interval_active: int = Field(..., gt=0)
    polling_interval_idle: int = Field(..., gt=0)

    bots: Dict[str, BotConfig]

    @model_validator(mode="before")
    @classmethod
    def gather_and_validate_bots(cls, values: dict[str, Any]) -> dict[str, Any]:
        """
        Pre-model build hook: collect bot_* entries into `bots`
        and inject shared paths.
        """
        bot_entries = {k: v for k, v in values.items() if k.startswith("bot_")}
        bots: Dict[str, BotConfig] = {}
        for name, conf in bot_entries.items():
            bot = BotConfig.model_validate(conf)
            if bot.download_path is None:
                bot.download_path = values["download_path"]
            if bot.chat_history_path is None:
                bot.chat_history_path = values["chat_history_path"]
            bots[name] = bot

        filtered = {k: v for k, v in values.items() if not k.startswith("bot_")}
        filtered["bots"] = bots
        return filtered


class FactoryDefault(BaseModel):
    command_prefix: str
    logging_enabled: bool
    history_enabled: bool
    history_file: str

    service: str
    model: str
    temperature: float = Field(..., ge=0.0, le=2.0)
    maxtoken: int = Field(..., gt=0)
    top_p: float = Field(..., ge=0.0, le=1.0)
    frequency_penalty: float
    presence_penalty: float


class ModelInfo(BaseModel):
    creator: str
    short: str
    release_year: str
    token_win: List[int]
    strengths: str
    weaknesses: str
    rank_power: str
    rank_coding: str
    rank_jail: str
    jailbreaks: List[str]
    details: str
    main_purpose: Optional[str] = None


class RootConfig(BaseModel):
    services: Dict[str, ServiceConfig]
    telegram: TelegramConfig
    factorydefault: FactoryDefault
    models_info: Dict[str, Dict[str, ModelInfo]]

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)
