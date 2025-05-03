# src/llm_telegram_bot/services/services_base.py
from abc import ABC, abstractmethod
from typing import Optional

from aiohttp import ClientTimeout

from llm_telegram_bot.config.schemas import ServiceConfig


class BaseLLMService(ABC):
    """
    Abstract base class for all LLM service providers.
    Now takes a typed ServiceConfig instead of a raw dict.
    """

    def __init__(self, config: ServiceConfig):
        # Required settings (validated by Pydantic)
        self.api_key: str = config.api_key
        self.endpoint: str = config.endpoint

        # Optional defaults
        self.model: Optional[str] = config.model

        # HTTP settings
        self.timeout: ClientTimeout = ClientTimeout(total=config.timeout)
        self.retries: int = config.retries

        # Extra model parameters (like top_p, frequency_penalty)
        self.model_params = config.model_params

    @abstractmethod
    async def send_prompt(self, prompt: str, model: Optional[str], temperature: float, maxtoken: int) -> str:
        """
        Send a prompt to the LLM service and return the response.

        Args:
            prompt: The input prompt.
            model: The model to use (can be None to use default).
            temperature: Sampling temperature.
            maxtoken: Max number of tokens to return.

        Returns:
            The LLM-generated response as a string.
        """
        pass

    def get_name(self) -> str:
        return self.__class__.__name__

    def get_default_model(self) -> Optional[str]:
        return self.model
