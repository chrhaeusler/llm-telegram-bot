# src/services/service_chutes.py

import logging
from typing import Optional

import aiohttp

from llm_telegram_bot.config.schemas import ServiceConfig

from .services_base import BaseLLMService

logger = logging.getLogger(__name__)


class ChutesService(BaseLLMService):
    """
    A class for interacting with the Chutes.ai LLM service.
    """

    def __init__(self, config: ServiceConfig, model_info: Optional[dict] = None):
        super().__init__(config)

        # Override default endpoint for Chutes
        self.endpoint = "https://llm.chutes.ai/v1/chat/completions"

        # Headers required by Chutes
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Optional model metadata
        self.model_info = model_info or {}

        # Default model already handled by BaseLLMService
        # Timeout is also inherited and used via self.timeout

    async def send_prompt(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        maxtoken: int = 512,
    ) -> str:
        """
        Send a prompt to the Chutes model and get a response.

        Args:
            prompt (str): The user input prompt.
            model (str): Optional override of the model name.
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
            "stream": False,
        }

        logger.debug(f"[Chutes] Sending prompt to {self.endpoint} using model={selected_model}")

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
                logger.error(f"[Chutes] Request failed: {e}")
                return f"Error from Chutes: {str(e)}"

    async def call(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> str:
        """
        Unified interface for testing and generic usage.
        """
        return await self.send_prompt(
            prompt=prompt,
            model=model,
            temperature=temperature,
            maxtoken=max_tokens,
        )
