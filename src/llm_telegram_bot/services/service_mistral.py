# src/providers/provider_mistral.py
import logging
from typing import Optional

import aiohttp
from aiohttp import ClientTimeout

from llm_telegram_bot.config.schemas import ServiceConfig

from .services_base import BaseLLMService

logger = logging.getLogger(__name__)


class MistralService(BaseLLMService):
    """
    Mistral LLM service implementation.
    Accepts a typed ServiceConfig instead of a raw dict.
    """

    def __init__(self, config: ServiceConfig):
        """
        Initialize the Mistral provider with validated configuration.
        """
        super().__init__(config)

        # Endpoint and API key already set by BaseLLMService
        # Override timeout if different from default
        self.timeout = ClientTimeout(total=config.timeout)

        # Prepare headers for requests
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
        Send a prompt to Mistral and return the assistant’s response.
        """
        selected_model = model or self.model

        payload = {
            "model": selected_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": maxtoken,
        }

        logger.debug(f"[Mistral] Sending request to {self.endpoint} with model={selected_model}")

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
                return f"Error from Mistral: {e}"

    async def call(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> str:
        """
        Unified test interface.
        """
        return await self.send_prompt(
            prompt=prompt,
            model=model,
            temperature=temperature,
            maxtoken=max_tokens,
        )
