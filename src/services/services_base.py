from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from aiohttp import ClientTimeout


class BaseLLMService(ABC):
    """
    Abstract base class for all LLM service providers (e.g., Groq, Mistral).
    Implementations should inherit from this and define required methods.
    """

    def __init__(self, config: Dict[str, Any]):
        api_key = config.get("api_key")
        if not isinstance(api_key, str):
            raise ValueError("Missing or invalid API key in config.")
        self.api_key: str = api_key

        endpoint = config.get("endpoint")
        if not isinstance(endpoint, str):
            raise ValueError("Missing or invalid endpoint in config.")
        self.endpoint: str = endpoint

        self.model: Optional[str] = config.get("model")
        self.timeout: ClientTimeout = ClientTimeout(total=config.get("timeout", 60))
        self.retries: int = config.get("retries", 2)

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
