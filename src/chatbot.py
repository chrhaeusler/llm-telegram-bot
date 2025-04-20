#!/usr/bin/env python3
"""
CLI Chat Interface for LLMs

This script provides an interactive CLI for chatting with a large language model.
It uses a default configuration from `../config/config.yaml` and supports session
persistence, response saving, and syntax highlighting based on content.

To Do:
- Console should allow to accept code block to be copy into it not just line
- being able to scroll up to previous commands at prompt would be awesome
- Bring print_help in line with commands available in telegram_utils (-> make a function)
- Use defaults from config.yaml ✅
- Implement all commands from telegram_utils.py
"""

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml
from colorama import Fore, Style
from colorama import init as colorama_init
from rich.console import Console
from rich.syntax import Syntax

from telegram_utils import (
    ChatSession,
    get_service_conf,
    load_models_info,
    load_yaml,
)

# Init formatting tools
colorama_init(autoreset=True)
console = Console(style="on #111111")

# Paths
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "../config/config.yaml"
MODELS_PATH = BASE_DIR / "../config/models_info.json"
TMP_DIR = BASE_DIR / "../tmp"
TMP_DIR.mkdir(exist_ok=True)

SAVE_ENABLED = False


def sanitize_filename(name: str) -> str:
    """Sanitize a string to make it a valid filename."""
    name = re.sub(r"[^\w\-.]", "_", name).strip("_")
    return name if "." in name else f"{name}.txt"


def save_response(response: str, suggested_filename: str):
    """Save a model's response to a file in TMP_DIR with timestamped filename."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    final_name = sanitize_filename(suggested_filename)
    full_path = TMP_DIR / f"{timestamp}_{final_name}"

    ext = full_path.suffix.lower()
    try:
        if ext == ".json":
            json.dump(
                {"response": response}, open(full_path, "w", encoding="utf-8"), indent=2
            )
        elif ext in (".yaml", ".yml"):
            yaml.dump({"response": response}, open(full_path, "w", encoding="utf-8"))
        else:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(response)
        print(
            f"{Style.DIM}{Fore.MAGENTA}💾 Saved to: {Fore.YELLOW}{full_path}{Style.RESET_ALL}"
        )
    except Exception as e:
        print(f"{Style.BRIGHT}{Fore.RED}❌ Failed to save file: {e}{Style.RESET_ALL}")


def prompt_filename_suggestion(session: ChatSession, reply: str) -> str:
    """Ask the LLM to suggest a filename for the last reply."""
    try:
        endpoint, api_key = get_service_conf(session.config, session.service)

        messages = [
            {
                "role": "user",
                "content": (
                    f"This was your last response:\n\n{reply}\n\n"
                    "Please suggest a very short file name (with extension) to save this reply. "
                    'Only respond with the file name in double quotes, like: "summary.md".'
                ),
            }
        ]

        resp = requests.post(
            endpoint,
            json={
                "model": session.model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 15,
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()["choices"][0]["message"]["content"].strip()
        print(f"🤖 Filename suggestion response: {result}")

        match = re.search(r'"([^\"]+\.[a-z0-9]+)"', result)
        if match:
            filename = sanitize_filename(match.group(1))
            print(f"📂 Using suggested filename: {filename}")
            return filename

        if "." in result:
            filename = sanitize_filename(result)
            print(f"📂 Using fallback filename: {filename}")
            return filename

        print("⚠️ No valid filename found. Using fallback.")
        return "output.txt"

    except Exception as e:
        print(f"⚠️ Failed to generate filename: {e}")
        return "output.txt"


def detect_language_block(text):
    """Try to guess the language of a code block for syntax highlighting."""
    if text.strip().startswith("{"):
        return "json"
    elif text.strip().startswith("#") or "#!/bin/bash" in text:
        return "bash"
    elif text.strip().startswith("def") or "import " in text:
        return "python"
    elif any(x in text for x in [":\n", "- ", "yaml"]):
        return "yaml"
    elif "# " in text or "**" in text:
        return "markdown"
    return None


def print_response_styled(reply: str):
    """Print bot reply with syntax highlighting if it's code."""
    language = detect_language_block(reply)
    if language:
        syntax = Syntax(reply, language, theme="monokai", line_numbers=False)
        console.print(syntax)
    else:
        print(f"{Style.BRIGHT}{Fore.GREEN}Bot:{Style.RESET_ALL} {reply}")


def print_help():
    """Return full help text for all supported commands."""
    return (
        "🛠️ Available commands:\n"
        "/help                - Show this help message\n"
        "/showsettings        - Show current session parameters\n"
        "/model               - Show info for current or named model\n"
        "/maxtokens <int>     - Set max tokens (e.g. 256)\n"
        "/temperature <float> - Set temperature\n"
        "/models              - Show models for current service\n"
        "/cmodel <name>       - Change to another model\n"
        "/services            - List available services\n"
        "/cservice <name>     - Change service\n"
        "/setasdefaults       - Save current settings to config.yaml\n"
        "/factoryreset        - Reset to factory defaults\n"
        "/save on             - Enable saving responses to ../tmp/\n"
        "/save off            - Disable saving responses\n"
        "\n💡 You can also enable saving from the start using `--save`"
    )


def main():
    """Main CLI entry point for the chatbot."""
    global SAVE_ENABLED

    parser = argparse.ArgumentParser(
        description="Chat with your configured LLM via CLI."
    )
    parser.add_argument("--service", help="Override the default service")
    parser.add_argument("--model", help="Override the default model")
    parser.add_argument("--temperature", type=float, help="Override temperature")
    parser.add_argument("--max_tokens", type=int, help="Override max tokens")
    parser.add_argument(
        "--save", action="store_true", help="Enable autosaving to ../tmp"
    )

    args = parser.parse_args()
    SAVE_ENABLED = args.save

    config = load_yaml(CONFIG_PATH)
    models_info = load_models_info(MODELS_PATH)

    # Apply CLI overrides to config
    default_conf = config.get("default", {})
    default_conf.update(
        {
            k: v
            for k, v in vars(args).items()
            if v is not None and k in ["service", "model", "temperature", "max_tokens"]
        }
    )

    session = ChatSession(config, models_info)
    session.service = default_conf.get("service", session.service)
    session.model = default_conf.get("model", session.model)
    session.temperature = default_conf.get("temperature", session.temperature)
    session.max_tokens = default_conf.get("max_tokens", session.max_tokens)

    print(
        f"\n{Style.BRIGHT}{Fore.CYAN}💬 CLI Chat Mode (type /help for commands, Ctrl+C to quit){Style.RESET_ALL}\n"
    )
    print(f"{Fore.CYAN}Service: {session.service}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Model: {session.model}")
    print(f"{Fore.CYAN}Max tokens: {session.max_tokens}")
    print(f"{Fore.CYAN}Temperature: {session.temperature}")
    print(f"{Fore.CYAN}Autosave: {SAVE_ENABLED} → ../tmp\n")

    try:
        while True:
            user_input = input(
                f"{Style.BRIGHT}{Fore.CYAN}You:{Style.RESET_ALL} "
            ).strip()
            if not user_input:
                continue

            if user_input.startswith("/"):
                if user_input == "/save on":
                    SAVE_ENABLED = True
                    print("✅ Autosave is now ON")
                    continue
                elif user_input == "/save off":
                    SAVE_ENABLED = False
                    print("✅ Autosave is now OFF")
                    continue
                elif user_input == "/help":
                    print(print_help())
                    continue

                reply = session.handle_command(user_input)
                print(f"🛠️ {reply}" if reply else "❌ Unknown command")
                continue

            try:
                endpoint, api_key = get_service_conf(session.config, session.service)
                payload = {
                    "model": session.model,
                    "messages": [{"role": "user", "content": user_input}],
                    "temperature": session.temperature,
                    "max_tokens": session.max_tokens,
                }
                resp = requests.post(
                    endpoint,
                    json=payload,
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=30,
                )
                resp.raise_for_status()
                reply = resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                reply = f"❌ API error: {e}"

            print_response_styled(reply)

            if SAVE_ENABLED:
                time.sleep(1)
                filename = prompt_filename_suggestion(session, reply)
                save_response(reply, filename)

    except KeyboardInterrupt:
        print(f"\n{Fore.MAGENTA}👋 Chat ended. Goodbye!")


if __name__ == "__main__":
    main()
