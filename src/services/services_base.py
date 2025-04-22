from abc import ABC
from typing import Any, Dict, Optional

from aiohttp import ClientTimeout


class BaseLLMService(ABC):
    """
    Abstract base class for all LLM service providers (e.g., Groq, Mistral).
    Implementations should inherit from this and define required methods.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the provider with credentials and optional default parameters.

        Args:
            config: Dictionary containing service configuration like API key, endpoint, timeouts, etc.
        """
        api_key = config.get("api_key")
        if not isinstance(api_key, str):
            raise ValueError("Missing or invalid API key in config.")
        self.api_key: str = api_key

        endpoint = config.get("api_key")
        if not isinstance(endpoint, str):
            raise ValueError("Missing or invalid API key in config.")
        self.endpoint: str = endpoint

        self.model: Optional[str] = config.get("model")
        self.timeout: ClientTimeout = ClientTimeout(total=config.get("timeout", 60))
        self.retries: int = config.get("retries", 2)

    def get_name(self) -> str:
        """
        Return a human-readable name for this provider.
        """
        return self.__class__.__name__

    def get_default_model(self) -> Optional[str]:
        """
        Return the default model configured for this provider.
        """
        return self.model
