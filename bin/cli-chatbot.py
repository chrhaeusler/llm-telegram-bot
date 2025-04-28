import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.theme import Theme

# Add the parent directory of `src` to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from src.telegram_utils import (
    ChatSession,
    build_startup_message,
    load_yaml,
)

BASE_DIR = Path(__file__).resolve().parent
CONFIG_YAML = (BASE_DIR / "../config/config.yaml").resolve()
MODELS_JSON = (BASE_DIR / "../config/models_info.json").resolve()


# === Defaults ===
DEFAULT_CHATBOT_CONF_PATH = Path("/config/chatbot.yaml")
DEFAULT_SAVE_DIR = Path("tmp")
DEFAULT_AUTOSAVE = False


custom_theme = Theme(
    {
        "markdown.code": "bold white on #1e1e1e",  # Match VSCode Dark+
        "markdown.text": "white",
        "markdown.h1": "bold cyan",
        "markdown.h2": "bold green",
        "markdown.h3": "bold yellow",
    }
)

console = Console(theme=custom_theme)


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
    syntax = detect_syntax(text)
    if syntax == "markdown":
        console.print(Markdown(text))
    else:
        console.print(Syntax(text, syntax, theme="vs-dark", line_numbers=False))


def load_chatbot_config(path: Path = DEFAULT_CHATBOT_CONF_PATH):
    if path.exists():
        return load_yaml(path)
    return {}


def parse_args():
    parser = argparse.ArgumentParser(description="CLI chatbot client for LLM services.")
    parser.add_argument("--save", dest="save", action="store_true", help="Enable autosaving output.")
    parser.add_argument(
        "--no-save",
        dest="save",
        action="store_false",
        help="Disable autosaving output.",
    )
    parser.set_defaults(save=None)
    return parser.parse_args()


def extract_filename(text: str) -> str:
    match = re.search(r'"([^"]+\.[a-zA-Z0-9]+)"', text)
    return match.group(1) if match else "chat_output.txt"


def save_response_to_file(response: str, save_dir: Path, filename: str = None):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%-M-%S")
    if not filename:
        filename = "chat_output.txt"
    save_path = save_dir / f"{timestamp}-{filename}"
    save_path.parent.mkdir(parents=True, exist_ok=True)
    print(response, response, response)
    print(save_path)
    with save_path.open("w", encoding="utf-8") as f:
        f.write(response.strip() + "\n")
    print(f"[📝 Saved to {save_path}]\n")


def main():
    args = parse_args()
    cli_conf = load_chatbot_config()
    autosave = cli_conf.get("autosave", DEFAULT_AUTOSAVE)
    save_dir = Path(cli_conf.get("save_dir", DEFAULT_SAVE_DIR))

    if args.save is not None:
        autosave = args.save

    config = load_yaml(CONFIG_YAML)
    models_info = load_yaml(MODELS_JSON)

    session = ChatSession(config=config, models_info=models_info)

    startup_msg = build_startup_message(
        session.service,
        session.model,
        session.temperature,
        session.max_tokens,
    )
    print(startup_msg)
    print("Type /exit or Ctrl+C to quit. Use /s before your message to save the response.\n")

    try:
        while True:
            user_input = input("\U0001f464 You: ").strip()

            if user_input.lower() in {"/exit", "/quit"}:
                print("\U0001f44b Bye!")
                break

            save_output = False
            if user_input.lower().startswith("/s "):
                save_output = True
                user_input = user_input[3:].strip()

            if user_input.startswith("/"):
                result = session.handle_command(user_input)
                if result:
                    print_output(result)
                continue

            response = session.query(user_input)
            print_output(response)

            if autosave or save_output:
                print("[💬 Debug: full response before saving:]\n")
                print_output(response)

                # Ask LLM for a filename
                prompt = (
                    f"This was your last response:\n\n{response}\n\n"
                    "Please suggest a very short file name (with extension) to save this reply.\n"
                    'Only respond with the file name in double quotes, like: "summary.md", "info.py".'
                )
                filename_suggestion = session.query(prompt)
                print(filename_suggestion)
                filename = extract_filename(filename_suggestion)

                save_response_to_file(response, save_dir, filename)

    except KeyboardInterrupt:
        print("\n\U0001f44b Exiting gracefully. See you soon!")


if __name__ == "__main__":
    main()
