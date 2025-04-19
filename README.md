# llm-telegram-bot

This project is a Python-based application that integrates with a free and uncensored LLM API via Telegram bot.

- [Mistral: Model overvie](https://docs.mistral.ai/getting-started/models/models_overview/)
- [Groq: Supported models](https://console.groq.com/docs/models)

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

# Install development dependencies
pip install -r requirements-dev.txt
```

4. Set up environment variables for the bot credentials
   s. config-template.yaml (save to config.yaml so it gets ignored by git)

### Create Telegram Bot

To get the Chat ID, visit:

- `https://api.telegram.org/bot63xxxxxx71:AAFoxxxxn0hwA-2TVSxxxNf4c/getUpdates"

## Requirements

- Python 3.10
- virtualenv
- Telegram Bot API token
- LLM API token from Services like Groq.com or Mistral.ai

## Usage

just type

```bash
python main.py
```
