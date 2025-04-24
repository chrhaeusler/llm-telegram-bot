# src/providers/provider_mistral.py

import logging
from typing import Optional

import aiohttp
from aiohttp import ClientTimeout

from .services_base import BaseLLMService

logger = logging.getLogger(__name__)


class MistralService(BaseLLMService):
    """
    A class that provides Mistral-specific methods for interacting with the Mistral LLM service.
    Inherits from BaseLLMService, which provides shared functionality across LLM providers.
    """

    def __init__(self, config: dict):
        """
        Initialize the Mistral provider, validating required configurations.

        Args:
            config (dict): A dictionary containing configuration for the provider
                           (e.g., api_key, endpoint).

        Raises:
            ValueError: If 'endpoint' is missing in the config.
        """
        super().__init__(config)

        endpoint = config.get("endpoint")
        if endpoint is None:
            raise ValueError("Missing required config key: 'endpoint'")
        self.endpoint: str = endpoint

        self.timeout = ClientTimeout(total=60)

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def send_prompt(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        maxtoken: int = 512,
    ) -> str:
        """
        Send a prompt to the Mistral service and get a response.

        Args:
            prompt (str): The user message to send.
            model (str): Model name (e.g., mistral-tiny).
            temperature (float): Sampling temperature.
            maxtoken (int): Maximum number of tokens in the reply.

        Returns:
            str: The assistant's response.
        """
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": maxtoken,
        }

        logger.debug(f"[Mistral] Sending request to {self.endpoint} with model={model}")

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
                logger.error(f"[Mistral] Request failed: {e}")
                return f"Error from Mistral: {str(e)}"

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
