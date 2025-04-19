"""
Test LLM API connectivity using the configuration in config/config.yaml.

This script:
- Loads the default service and model specified in the config
- Sends a simple prompt to test the service
- Uses a timeout to avoid hanging
- Handles errors gracefully
"""

import requests
import yaml

CONFIG_PATH = "config/config.yaml"
TIMEOUT_SECONDS = 15  # Max time to wait for a response from the API


def load_config(path: str) -> dict:
    """Load YAML configuration file from the given path."""
    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def get_service_settings(config: dict) -> tuple:
    """Extract active service settings from the config."""
    service_name = config.get("default", {}).get("service")
    services = config.get("services", {})

    if not service_name or service_name not in services:
        raise ValueError(
            f"Invalid or missing default service '{service_name}' in config."
        )

    service_config = services[service_name]

    if not service_config.get("enabled", False):
        raise ValueError(f"The selected service '{service_name}' is not enabled.")

    if "api_key" not in service_config:
        raise ValueError(f"API key missing for service '{service_name}'.")

    return service_name, service_config


def test_llm_api():
    """Send a test prompt to the selected LLM service and print the response."""
    config = load_config(CONFIG_PATH)
    service_name, service_config = get_service_settings(config)

    url = service_config["endpoint"]
    api_key = service_config["api_key"]
    model = service_config["model"]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hello, who are you?"}],
    }

    try:
        response = requests.post(
            url, headers=headers, json=payload, timeout=TIMEOUT_SECONDS
        )
        response.raise_for_status()
        result = response.json()
        message = result["choices"][0]["message"]["content"]
        print(f"Response from {service_name} ({model}):\n{message}")

    except requests.exceptions.Timeout:
        print(f"Request to {service_name} timed out after {TIMEOUT_SECONDS} seconds.")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except KeyError:
        print("Unexpected response format.")
        print(response.text)


if __name__ == "__main__":
    test_llm_api()
