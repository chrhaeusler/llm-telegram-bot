# 🤖 llm-telegram-bot

A lightweight, modular Telegram chatbot framework. It proxies messages between a Telegram chat and one of multiple Large Language Model (LLM) services, while maintaining a persistent, tiered memory.

Built in Python, it runs smoothly on resource‑constrained hardware (e.g. Raspberry Pi) and is highly configurable for persona management, summarization strategies, and LLM provider integration.

> ⚠️ Currently, in **Alpha testing phase** (aka "it works on my computers and I am pretty happy with it"); won’t "just work" by `pip install`; s. [issues.md](/issues.md) for the current state of the project's roadmap; do not expect major changes before my next holidays.

## What It Does

- **Multi‑Provider Support**: Out‑of‑the‑box adapters for [groq.com](https://console.groq.com/docs/models), [mistral.ai](https://docs.mistral.ai/getting-started/models/models_overview/), [chutes.ai](https://chutes.ai/app?type=llm).
- **In‑Chat Commands**: e.g., `/help`, `/service`, `/model`, `/bot` etc. (s. [in-chat commands](/config/commands.yaml)).
- **Char & User Profiles**: Configure different roles for the LLM and user via YAML; switch on‑the‑fly with `/char` and `/user`.
- **Tiered Memory**: Maintains multi-tier conversational memory with increasing summarization / compression.
- **Dynamic Prompt Composition**: Injects system instructions, context blocks, summaries of earlier messages, and recent messages into each prompt.

## If you do not have a Telegram Bot yet...

1. Send a message to @BotFather and create a bot by typing `/newbot`; you will get the bot's API key from BotFather the moment you created the bot
2. Send a message to your bot (to open a chat with the bot)
3. To get the chat ID, visit (substitute 123456...zzzz with your bot's API key):
   - `https://api.telegram.org/bot12345678:xxxxxxxxxx:yyyyyyyyyyyyy_zzzzzzzzzzzzzzzzzzzzz/getUpdates"

## Usage

adjust:

- [config-template.yaml](/config/config-template.yaml) (note: outdated!)
- [role config of LLM char](config/chars/char_template.yaml)
- [role config of user chars](/config/users/user_template.yaml)

```bash
./run.sh
```
