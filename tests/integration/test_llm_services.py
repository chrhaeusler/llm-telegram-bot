#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

# run with "PYTHONPATH=src python tests/integration/test_llm_services.py"

# Add the src directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Now we can import from src
from config_loader import config_loader
from services.service_groq import GroqService
from services.service_mistral import MistralService


async def test_service(service_class, service_name, model_name):
    print(f"\n🚀 Testing {service_name} / {model_name}")
    # Load your unified config
    config = config_loader("config/config.yaml")
    # Extract the service-specific part
    service_config = config["services"].get(service_name)
    if not service_config:
        print(f"❌ No config found for service: {service_name}")
        return

    # Instantiate the service
    service = service_class(config=service_config)

    prompt = "Say hello in a friendly tone"
    # Try to pick up defaults if you set them in config/services
    temperature = service_config.get("temperature", 0.7)
    maxtoken = service_config.get("maxtoken", 100)

    try:
        # Note: new method name is send_prompt(...)
        response = await service.send_prompt(
            prompt=prompt,
            model=model_name,
            temperature=temperature,
            maxtoken=maxtoken,
        )
        # Truncate for readability
        snippet = response[:200] + ("..." if len(response) > 200 else "")
        print("✅ Response:", snippet)
    except Exception as e:
        print(f"❌ Error calling {service_name}: {e}")


async def main():
    await test_service(GroqService, "groq", "compound-beta-mini")
    await test_service(MistralService, "mistral", "pixtral-12b-2409")


if __name__ == "__main__":
    asyncio.run(main())
