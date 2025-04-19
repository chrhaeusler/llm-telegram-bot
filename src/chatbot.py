#!/usr/bin/env python3
"""
Chatbot Script for Interacting with LLM Services (Groq, Mistral, etc.)

Usage:
    python chatbot.py
    python chatbot.py --service groq --model llama3-70b-8192 --temperature 0.5 --max_tokens 250

Supports in-chat commands:
    /model <model_name>
    /service <service_name>
    /temp <float_value>
    /max_tokens <int_value>
    /help

Configuration is loaded from config/config.yaml
"""

import argparse
import os
import sys

import requests
import yaml

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/config.yaml")


def load_config(path=CONFIG_PATH):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def get_service_config(config, service_name):
    service = config["services"].get(service_name)
    if not service or not service.get("enabled", False):
        raise ValueError(f"Service '{service_name}' is not enabled or not configured.")
    api_key = service.get("api_key") or service.get("apy_key")  # handle typo fallback
    if not api_key:
        raise ValueError(f"API key missing for service '{service_name}'.")
    return {
        "api_key": api_key,
        "model": service.get("model"),
        "endpoint": service.get("endpoint"),
    }


def send_message(service_conf, messages, temperature, max_tokens):
    headers = {
        "Authorization": f"Bearer {service_conf['api_key']}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": service_conf["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        response = requests.post(
            service_conf["endpoint"], json=payload, headers=headers, timeout=20
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.RequestException as e:
        return f"❌ API error: {str(e)}"
    except (KeyError, IndexError):
        return "❌ Unexpected response from API."


def print_help():
    return (
        "🛠️ Available commands:\n"
        "/service <service_name>  - Switch service (e.g. groq, mistral)\n"
        "/model <model_name>      - Change model (must be valid for current service)\n"
        "/temp <float>            - Change temperature (e.g. 0.7)\n"
        "/max_tokens <int>        - Change max tokens (e.g. 200)\n"
        "/help                    - Show this help message"
    )


def main():
    parser = argparse.ArgumentParser(description="Chat with a configured LLM service.")
    parser.add_argument(
        "--service", default=None, help="LLM service to use (e.g., groq, mistral)"
    )
    parser.add_argument("--model", default=None, help="Model to use")
    parser.add_argument(
        "--temperature", type=float, default=0.7, help="Sampling temperature"
    )
    parser.add_argument(
        "--max_tokens", type=int, default=100, help="Max tokens in response"
    )

    args = parser.parse_args()

    config = load_config()
    current_service = args.service or config["default"]["service"]
    temperature = args.temperature
    max_tokens = args.max_tokens

    try:
        service_conf = get_service_config(config, current_service)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    if args.model:
        service_conf["model"] = args.model

    print(f"\nUsing service: {current_service}")
    print(f"Using model: {service_conf['model']}")
    print(f"Temperature: {temperature}")
    print(f"Max tokens: {max_tokens}")
    print("\nChat mode: Type your messages (Ctrl+C to exit)...\n")

    messages = [{"role": "system", "content": "You are a helpful assistant."}]

    try:
        while True:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                try:
                    cmd, *params = user_input[1:].split()
                    if cmd == "help":
                        print(print_help())
                    elif cmd == "service":
                        new_service = params[0]
                        try:
                            new_conf = get_service_config(config, new_service)
                            current_service = new_service
                            service_conf = new_conf
                            print(f"✅ Switched to service: {new_service}")
                        except ValueError as e:
                            print(f"❌ {e}")
                    elif cmd == "model":
                        new_model = params[0]
                        service_conf["model"] = new_model
                        print(f"✅ Model set to: {new_model}")
                    elif cmd == "temp":
                        temperature = float(params[0])
                        print(f"✅ Temperature set to: {temperature}")
                    elif cmd == "max_tokens":
                        max_tokens = int(params[0])
                        print(f"✅ Max tokens set to: {max_tokens}")
                    else:
                        print("❌ Unknown command. Use /help")
                except (IndexError, ValueError):
                    print("❌ Invalid command format. Use /help")
                continue

            messages.append({"role": "user", "content": user_input})
            reply = send_message(service_conf, messages, temperature, max_tokens)
            messages.append({"role": "assistant", "content": reply})
            print(f"Bot: {reply}")

    except KeyboardInterrupt:
        print("\n👋 Chat ended. Goodbye!")


if __name__ == "__main__":
    main()
