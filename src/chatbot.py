import argparse
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax

# Add the parent directory of `src` to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from src.telegram_utils import (
    ChatSession,
    get_service_conf,
    load_yaml,
    send_message,
)

# Add the parent directory of `src` to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_DIR = Path(__file__).resolve().parent
CONFIG_YAML = (BASE_DIR / "../config/config.yaml").resolve()
MODELS_JSON = (BASE_DIR / "../config/models_info.json").resolve()

# Initialize console for rich output
console = Console()

# === Defaults ===
DEFAULT_CHATBOT_CONF_PATH = Path("../config/chatbot.yaml")
DEFAULT_SAVE_DIR = Path("../tmp")
DEFAULT_AUTOSAVE = False


# === Detect file type for code syntax highlighting ===
def detect_syntax(text: str) -> str:
    if text.lstrip().startswith("{"):
        return "json"
    if text.lstrip().startswith("```") and text.rstrip().endswith("```"):
        lang = text.lstrip()[3:].splitlines()[0].strip()
        return lang if lang else "markdown"
    if text.lstrip().startswith("#!"):
        return "bash"
    return "markdown"


def print_output(text: str):
    """Pretty print LLM output with syntax highlighting."""
    syntax = detect_syntax(text)
    if syntax == "markdown":
        console.print(Markdown(text))
    else:
        console.print(Syntax(text, syntax, theme="monokai", line_numbers=False))


def load_chatbot_config(path: Path = DEFAULT_CHATBOT_CONF_PATH):
    if path.exists():
        return load_yaml(path)
    return {}


def parse_args():
    parser = argparse.ArgumentParser(description="CLI chatbot client for LLM services.")
    parser.add_argument(
        "--save", dest="save", action="store_true", help="Enable autosaving output."
    )
    parser.add_argument(
        "--no-save",
        dest="save",
        action="store_false",
        help="Disable autosaving output.",
    )
    parser.set_defaults(
        save=None
    )  # So we can distinguish between unset vs explicit override
    return parser.parse_args()


def main():
    args = parse_args()

    # Load CLI-specific config
    cli_conf = load_chatbot_config()
    autosave = cli_conf.get("autosave", DEFAULT_AUTOSAVE)
    save_dir = Path(cli_conf.get("save_dir", DEFAULT_SAVE_DIR))

    # CLI override
    if args.save is not None:
        autosave = args.save

    # Load the configuration and models info from YAML files
    # Use load_yaml to load the files into dictionaries
    config = load_yaml(CONFIG_YAML)
    models_info = load_yaml(MODELS_JSON)

    # Retrieve token and chat_id from the config
    token = config.get("telegram", {}).get("bot_token")
    chat_id = config.get("telegram", {}).get("chat_id")
    # Prepare session
    session = ChatSession(config=config, models_info=models_info)

    print("\n💬 Welcome to the CLI chatbot!")
    print("Type your message, or use commands like /models, /cmodel <name>, /help")
    print("Type /exit or Ctrl+C to quit.\n")

    try:
        while True:
            user_input = input("👤 You: ").strip()

            if user_input.lower() in {"/exit", "/quit"}:
                print("👋 Bye!")
                break

            if user_input.startswith("/"):
                result = session.handle_command(user_input)
                if result:
                    print_output(result)
                continue

            send_message(token, chat_id, user_input)

            if autosave:
                model = session.model
                conf = get_service_conf(session.service)
                filename = conf.get("filename_suggestion", "chat_output.txt")
                save_path = save_dir / filename
                save_path.parent.mkdir(parents=True, exist_ok=True)
                with save_path.open("a", encoding="utf-8") as f:
                    f.write(f"\nUser: {user_input}\nBot: {response}\n")

                print(f"[💾 Saved to {save_path}]\n")

            print_output(user_input)

    except KeyboardInterrupt:
        print("\n👋 Exiting gracefully. See you soon!")


if __name__ == "__main__":
    main()
