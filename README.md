# 🚧 llm-telegram-bot (Alpha)

> **⚠️ Alpha quality** – may break, incomplete setup, won’t “just work” by `pip install`.  
> Frequent breaking changes. Use at your own risk.

---

## Project Goal

- **Bridge** Telegram ↔️ multiple LLM services  
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