# llm-telegram-bot

A lightweight Python bot that proxies messages between Telegram and various LLM APIs.  
Modular, configurable, and extendable—switch services, models, temperature, and token limits on the fly.

## Features

- **Multi‑service support**: [Mistral AI](https://docs.mistral.ai/getting-started/models/) and [Groq: Supported models](https://console.groq.com/docs/rate-limits) (add more via config)
- **Dynamic model switching**: chat commands `/models`, `/cmodel <name>`
- **Service switching**: chat commands `/services`, `/cservice <name>`
- **Runtime parameter tuning**: chat commands `/temperature <float>`, `/maxtokens <int>`
- **Persistence**: save defaults (`/setasdefaults`), factory reset (`/factoryreset`), show settings (`/showsettings`)
- **Model listings**: chat command `/models`
- **Model information**: chat command `/model`
- **Graceful backoff**: idle vs active polling intervals, exponential backoff
- **Error handling**: API errors forwarded into the chat

## Prerequisites

- Python ≥ 3.10
- `venv` or `virtualenv`
- Telegram Bot API token
- LLM API keys (Mistral, Groq, etc.)

## Setup

### This repository

1. Clone the repository

```bash
git clone git@github.com:chrhaeusler/llm-telegram-bot.git
```

2. Set up a Python virtual environment

```bash
# Create a virtual environment
python3 -m venv .venv
# Activate the virtual environment (optional, but recommended)
# On Windows: .venv\Scripts\activate
source .venv/bin/activate
```

3. Install dependencies

```bash
# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy the template to config.yaml (untracked by git) and fill in your tokens & settings

```bash
cp config/config-template.yaml config/config.yaml
```

### If you do not have a Telegram Bot yet...

1. Send a message to @BotFather and create a bot by typing `/newbot`; you will get the bot's API key from BotFather the moment you created the bot
2. Send a message to your bot (to open a chat with the bot)
3. To get the chat ID, visit (substitute 123456...Nf4c with your bot's API key):
   - `https://api.telegram.org/bot12345678:xxxxxxxxxx:yyyyyyyyyyyyy_zzzzzzzzzzzzzzzzzzzzz/getUpdates"

## Usage

```bash
python main.py
```

---

---

## To Do

- keep original file name for downloads
- use polling_active_for instead of hard coded 5 minutes
  add the new commands from updated commands.yaml
- Adding LLM memory or context chaining
- requirements.txt vs requirements-dev.txt
- Add a setup.py or pyproject.toml
- CI pipeline: lint (ruff), type‑check (mypy), format (black), run tests.
- Add more LLM services (e.g. [Free LLM Ressources ](https://github.com/cheahjs/free-llm-api-resources))

Long-term plan

```bash
├── bin/
│   └── cli-chatbot.py              # To Do: Entry point for CLI interaction
├── config/
│   ├── commands.yaml               # To Do: Supported commands and metadata (later implementation)
│   ├── config.yaml                 # 0. Main app config (providers, polling, etc.)
│   └── models_info.json            # 0. Existing (revise): Model descriptions/details
├── logs/
├── main.py                         # To Do: Optional: unified app launcher (later, if needed)
├── README.md
├── src/
│   ├── __init__.py
│   ├── config_loader.py            # 1. Existing (revise): Handles loading and validating config files
│   ├── telegram/
│   │   ├── __init__.py
│   │   ├── poller.py
│   │   ├── routing.py              # 6. To Do: Parses Telegram messages and routes actions
│   │   └── client.py               # 5 Existing (revise): Telegram API interface (message handling)
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── provider_base.py        # 2. To Do: Interface/base class for LLM providers
│   │   ├── groq_api.py             # 3. To Do: for groq.com API (LLM provider)
│   │   └── mistral_api.py          # 4. To Do: for mistral.ai API (LLM provider)
│   ├── commands/                   # To Do: Command handling directory
│   │   ├── __init__.py             # To Do: Initialization for commands module
│   │   ├── parser.py               # To Do: Recognizes commands and handles execution
│   │   ├── show.py                 # To Do: Commands to show info about the current model, services, etc.
│   │   ├── send.py                 # To Do: Commands to send LLM replies or input to file
│   │   ├── change.py               # To Do: Commands to change service, model, parameters, etc.
│   │   ├── saverestore.py          # To Do: Commands for saving/restoring chat history
│   │   └── jailbreaks.py           # To Do: Standard jailbreak prompt logic
│   ├── storage/                    # To Do: File saving and history logging
│   │   ├── __init__.py             # To Do: Initialization for storage module
│   │   ├── saver.py                # To Do: File saving utilities (/s, /s0, etc.)
│   │   └── history_logger.py       # To Do: Logs ongoing chat to file (if enabled)
│   └── utils/
│       ├── __init__.py
│       └── helpers.py              # To Do: Common utilities (timestamps, formatting, etc.)
├── tests/
│   └── test_main.py                # To Do: Tests for the integrated functionality (full flow)
└──  tmp/

```

```
config.py   src/config_loader.py
client.py	src/telegram/client.py
commands.py	src/commands/parser.py and jailbreaks.py
dispatcher.py	src/telegram/routing.py
memory.py	src/storage/history_logger.py
llm_interface.py	src/llm/*_api.py + provider_base.py
utils.py	src/utils/helpers.py
```
