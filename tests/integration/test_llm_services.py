# tests/integration/test_llm_services.py

import pytest

from src.config_loader import config_loader
from src.services.service_groq import GroqService
from src.services.service_mistral import MistralService


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("service_class", "service_name", "model_name"),
    [
        (GroqService, "groq", "compound-beta-mini"),
        (MistralService, "mistral", "pixtral-12b-2409"),
    ],
)
async def test_llm_service_endpoint(service_class, service_name, model_name):
    """
    Verifies that each LLM service can be instantiated and will
    return a non‐empty string for a simple prompt.
    """
    # load your unified YAML config
    cfg = config_loader()

    # pull out just this service’s config
    svc_conf = cfg["services"].get(service_name)
    assert svc_conf is not None, f"No config for service '{service_name}'"

    service = service_class(config=svc_conf)

    prompt = "Say hello in a friendly tone"
    temperature = svc_conf.get("temperature", 0.7)
    maxtoken = svc_conf.get("maxtoken", 128)

    reply = await service.send_prompt(
        prompt=prompt,
        model=model_name,
        temperature=temperature,
        maxtoken=maxtoken,
    )

    # sanity‐check
    assert isinstance(reply, str)
    assert reply.strip(), "Expected a non‐empty reply"
