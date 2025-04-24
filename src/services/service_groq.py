# src/services/service_groq.py

import logging
from typing import Optional

import aiohttp
from aiohttp import ClientTimeout

from .services_base import BaseLLMService

logger = logging.getLogger(__name__)


class GroqService(BaseLLMService):
    """
    A class for interacting with the Groq LLM service.
    Inherits from BaseLLMService, which provides API key loading and shared logic.
    """

    def __init__(self, config: dict, model_info: Optional[dict] = None):
        """
        Initialize the Groq service with configuration and optional model metadata.

        Args:
            config (dict): Configuration containing keys like 'endpoint', 'api_key', 'default_model'.
            model_info (dict | None): Optional model metadata loaded from models_info.json.
        """
        super().__init__(config)

        endpoint = config.get("endpoint")
        if endpoint is None:
            raise ValueError("Missing required config key: 'endpoint'")
        self.endpoint: str = endpoint

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        self.timeout = ClientTimeout(total=60)

        # Store model info for later use (optional)
        self.model_info = model_info or {}

        # Default model if not specified in prompt or call
        self.model = config.get("default_model", "compound-beta-mini")

    async def send_prompt(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        maxtoken: int = 512,
    ) -> str:
        """
        Send a prompt to the Groq model and get a response.

        Args:
            prompt (str): The user input prompt.
            model (str): The model name (default: self.model).
            temperature (float): Controls randomness in output.
            maxtoken (int): Max tokens to generate.

        Returns:
            str: The LLM's response text.
        """
        selected_model = model or self.model

        payload = {
            "model": selected_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": maxtoken,
        }

        logger.debug(
            f"[Groq] Sending prompt to {self.endpoint} using model={selected_model}"
        )

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.endpoint,
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout,
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]

            except Exception as e:
                logger.error(f"[Groq] Request failed: {e}")
                return f"Error from Groq: {str(e)}"

    async def call(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> str:
        """
        Unified interface for testing and generic usage.

        Args:
            prompt (str): The user prompt.
            temperature (float): Sampling temperature.
            max_tokens (int): Maximum tokens to generate.
            model (str | None): Optional override of the model to use.

        Returns:
            str: The model response.
        """
        return await self.send_prompt(
            prompt=prompt,
            model=model,
            temperature=temperature,
            maxtoken=max_tokens,
        )
