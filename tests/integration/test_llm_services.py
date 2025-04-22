# run with "PYTHONPATH=src python tests/integration/test_llm_services.py"
import asyncio
import sys
from pathlib import Path

# Add the src directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Now we can import from src
from config_loader import load_config
from services.service_groq import GroqService
from services.service_mistral import MistralService


async def test_service(service_class, service_name, model_name):
    print(f"\n🚀 Testing {service_name} / {model_name}")
    config = load_config()

    service_config = config["services"].get(service_name)
    if not service_config:
        print(f"❌ No config found for service: {service_name}")
        return

    service = service_class(config=service_config)
    prompt = "Say hello in a friendly tone"
    try:
        result = await service.call(prompt=prompt, model=model_name)
        print("✅ Response:", result[:200], "..." if len(result) > 200 else "")
    except Exception as e:
        print(f"❌ Error calling {service_name}: {e}")


async def main():
    await test_service(GroqService, "groq", "compound-beta-mini")
    await test_service(MistralService, "mistral", "pixtral-12b-2409")


if __name__ == "__main__":
    asyncio.run(main())
