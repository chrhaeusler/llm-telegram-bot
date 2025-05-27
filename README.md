# 🚧 llm-telegram-bot (Alpha)

> **⚠️ Alpha quality** (aka "it works on my computer") – won’t "just work" by `pip install`; frequent breaking changes.

## Note

This readme is outdated every couple of days, so I'll stop updating it until the package
is in beta (s. [issues.md](/issues.md) for the current state). Anyhow:

A lightweight Python bot that proxies messages between Telegram and various LLM APIs.
Modular, configurable, and extendable—switch services, models, temperature, and token limits on the fly.

## Project Goal

- **Bridge** Telegram ↔️ multiple LLM services ([groq.com](https://console.groq.com/docs/models), [mistral.ai](https://docs.mistral.ai/getting-started/models/models_overview/), [chutes.ai](https://chutes.ai/app?type=llm))
- **Maintain** conversational memory with tiered summarization
- **Highly** configurable: services, models, tokens, personas

### Sub-goals

1. **Char/User Management**  
   – pick personas with `/char`, `/user`
2. **Stateless Routing & Polling**  
   – `poller.py` receives updates, dispatches to LLM or handlers
3. **In-chat Commands**  
   – `/help`, `/service`, `/model`, `/history`, `/slp`, `/slr`
4. **History Manager**  
   – Tier-0 raw, Tier-1 midterm summaries, Tier-2 “mega” summaries  
   – auto-promote & cap tokens
5. **Prompt Builder**  
   – inject `[SYSTEM]`, `[OVERVIEW]`, `[SUMMARY]`, `[RECENT]`, `[PROMPT]`

## Project Logic

1. **Startup**
   - `run.sh` sets `PYTHONPATH`, NLTK data, spawns virtualenv, invokes `poller.py`
2. **PollingLoop (poller.py)**
   - instantiates `Session`, `HistoryManager`
   - on text: detect language, build full prompt from context, call LLM service, record reply
3. **Session & HistoryManager**
   - `Session.history_mgr` holds 3 deques (tier0,1,2)
   - Just-in-time compress tier0 entries, `_maybe_promote()` to tier1 & tier2
   - periodic & manual flush to JSON files, load on persona switch & startup
4. **Prompt Assembly**
   - `build_full_prompt()` concatenates:
     1. rendered system/Jailbreak
     2. `[OVERVIEW]` (tier-2 mega summaries)
     3. `[SUMMARY]` (tier-1 summaries)
     4. `[RECENT]` (tier-0 compressed/raw)
     5. `[PROMPT]` user’s new message
5. **Commands**
   - `/history` controls logging & flush/load
   - `/slp`, `/slr` save last prompt/response from tier-0

## If you do not have a Telegram Bot yet...

1. Send a message to @BotFather and create a bot by typing `/newbot`; you will get the bot's API key from BotFather the moment you created the bot
2. Send a message to your bot (to open a chat with the bot)
3. To get the chat ID, visit (substitute 123456...zzzz with your bot's API key):
   - `https://api.telegram.org/bot12345678:xxxxxxxxxx:yyyyyyyyyyyyy_zzzzzzzzzzzzzzzzzzzzz/getUpdates"

## Usage

```bash
./run.sh
```
