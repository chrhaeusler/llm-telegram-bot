# WIP: llm-telegram-bot

## Note

This readme is outdated every couple of days, so I'll stop updating it until the package
is in beta (s. [issues.md](/issues.md) for the current state). Anyhow:

A lightweight Python bot that proxies messages between Telegram and various LLM APIs.
Modular, configurable, and extendable—switch services, models, temperature, and token limits on the fly.

## Features

- **Multi‑service support**: [Mistral AI](https://docs.mistral.ai/getting-started/models/) and [Groq: Supported models](https://console.groq.com/docs/models) (add more via config)
- **In-chat help**: chat command `/help`
- **Service switching**: chat commands `/services`, `/service <int>`
- **Dynamic model switching**: chat commands `/models`, `/model <int>`
- **Model listings**: chat command `/models`
- **Model information**: chat command `/model`
- **Runtime parameter tuning**: chat commands `/temp <float>`, `/tokens <int>`
- **User & Chars**: chat commands `/users`, `/user`, and `/chars`, `/char`
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
./run.sh
```
