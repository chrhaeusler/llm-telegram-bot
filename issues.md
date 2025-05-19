# Project Roadmap (Updated 2025-05-13)

## Phase 0 – Development Infrastructure & CI

- [ ] Add & configure pre-commit hooks (black, isort, flake8, mypy)
- [ ] Enforce mypy typing on all public interfaces
- [ ] Create a lightweight CI pipeline to run pre-commit, pytest, mypy
- [ ] Fix: sent pictures are not correctly saved to disk
- [ ] Add CI status badges to README

## Phase 1 – Core Foundations & “Simple” Commands ✅

- [x] Load command handlers (`@register_command`) in poller
- [x] Help & view commands: `/help`, `/bot(s)`, `/model(s)`, `/status`
- [x] Set/override commands: `/temp`, `/tokens`, `/service`, `/model`
- [x] File I/O commands: `/savestr`, `/slp`, `/slr`
- [ ] Refactor handlers to rely on session state rather than disk I/O
- [ ] Unit tests for all Phase 1 handlers

## Phase 2 – Session Manager & State Isolation ✅

- [x] `session_manager.py` refactored: per-bot, per-chat-ID state
- [x] Default service/model seeded from config
- [ ] Unit tests for session state behaviors

## Phase 3 – Persona & History Commands ✅

### 3.1 Persona Commands

- [x] Load/validate `/char` and `/user` YAMLs (`char_loader.py`)
- [x] commands `/char`, `/user`
- [x] Flush & reload history on persona switch (no duplicates!)
- [ ] Unit tests for all persona commands

### 3.2 History I/O Commands

- [x] `/history on|off|files|load|flush`
- [x] Automatic load on startup (latest session file)
- [x] Manual flush merges new entries into JSON (rotating version if too large)
- [ ] Fix entries of `[Recent]` and do not include API errors like `LLM Char: Error from Groq: 429, message='Too Many Requests', url='https://api.groq.com/openai/v1/chat/completions'`; `Error from Groq: 429, message='Too Many Requests', url='https://api.groq.com/openai/v1/chat/completions'`; or just `Error from Groq: ` dont know why it is so short?
- [ ] Unit tests for `/history` behaviors

## Phase 4 – History Summarization (🟡 In Progress)

### 4.1 Tier-0 “Just-In-Time” Compression

- [x] if message > T0_cap, call `safe_summarize(..., sentences=T0_cap/avg)`
- [ ] fix: now both tokens_text and tokens_compressed; but we need just tokens_text
- [ ] fix add `lang` for language instead

### 4.2 Tier-1 Promotion

- [x] When `len(tier0)>N0`, pop oldest, summarize to ≤ T1_cap tokens, wrap in `Summary`
- [x] `Summary` now carries `ts`, `who`, `text`, `tokens`
- [ ] add `lang`

### 4.3 Tier-2 Rolling “Mega” Summaries

- [x] When `len(tier1)>N1`, batch a fraction (25% of N1) or up to `K`, combine, prepend previous mega
- [x] Extract detecting-language, steering prompt, `safe_summarize(..., sentences=MEGA_SENTENCES)`
- [x] Extract & merge NER keywords (limit to `MAX_KEYWORDS`, FIFO)
- [ ] Fix: Extract NERs before combining (possibly english and german summaries)!
- [ ] `MegaSummary` holds `text`, `keywords`, `tokens`, `span_start`, `span_end`, `lang`, `source_blob`, `is_stub`

### 4.4 Prompt Assembly & Injection

- [x] build_full_prompt() order:
  1. System / jailbreak
  2. `[CONTEXT]` (timestamps & “last at…”)
  3. `[OVERVIEW]` → tier2.megas
  4. `[SUMMARY]` → tier1
  5. `[RECENT]` → tier0 (use `msg.compressed`)
  6. `[PROMPT]` → user text

### 4.5 Nice-to-Have: Time Awareness

- [ ] Before `[PROMPT]`, inject a small block: `[CONTEXT]`: `Last message at {last_msg.ts} by {last_msg.who}. Current time is {now} to provide Weekday and Time of Day
- [ ] Support Jinja in char config to adapt replies if gap of >2h
- [ ]Support Jinja in persona templates for time-aware behavior

```jinja
{% if (now - last_msg_dt).hours >= 2 %}
  Wenn zwischen …
{% endif %}
```

## Phase 5 – Configuration & Tuning

- [ ] Move `N0`, `N1`, `K`, `T0_cap`, `T1_cap`, `T2_cap`, etc. into `config.yaml` per-bot
- [ ] Read parameters at startup and pass into `HistoryManager`
- [ ] Expose `/sum [params]` to tweak summarization on the fly
- [ ] Switch from word counts to real token counts (e.g. tiktoken)

## Phase 6 – Logging, Formatting & CLI 🟡

- [x] Enhanced send_message logs (chat_id, duration, preview)
- [x] HTML‐safe escapes for all outgoing messages
- [x] telegram_splitter.py for Telegram’s 4096-char limit
- [ ] CLI runner (bin/cli-chatbot.py) with Markdown rendering
- [ ] Update README.md with examples

## Phase 7 – Mid-Term & Testing

- [ ] Add unit tests for each tier’s summarization logic & metrics (token savings)
- [ ] Implement CI “smoke test”: Telegram → LLM end-to-end
- [ ] Auto-reload tier1/tier2 on startup if file exists
- [ ] Migrate raw history from JSON → SQLite or vector DB

## Phase 8 – Nice-to-Have Commands

- [ ] `/dlm`: delete the last message in the history buffer and historyManager
- [ ] `/undo`, `/reset`, `/defaults`, `/jb` (auto jailbreaks)
- [ ] `/memory` to inspect current tiers
- [ ] Explore speech-to-text, text-to-speech, image analysis, etc.

# Project Structure & Status (Updated 2025-05-04)

```bash
├── bin
│   └── cli-chatbot.py                # [ ] CLI entrypoint (Phase 5) – stub, not implemented yet
├── config
│   ├── chars
│   │   └── char_template.yaml        # [x] Character YAML template (Phase 3)
│   ├── commands.yaml                 # [x] Command definitions (used by `/help`, registry)
│   ├── config-template.yaml          # [ ] Template for config.yaml (needs update)
│   ├── config.yaml                   # [x] Active bot & LLM settings (loaded & validated)
│   ├── models_info.json              # [x] Model metadata (used by `/models`, `/model`)
│   └── users
│       └── user_template.yaml        # [x] User profile YAML template (Phase 3)
├── issues.md                         # [x] High-level issues & notes
├── LICENSE                           # [x] Project license
├── logs                              # [x] Runtime logs (auto-generated)
├── poetry.lock                       # [x] Locked dependencies
├── pyproject.toml                    # [x] Project metadata & tools (poetry, black, ruff, mypy)
├── README.md                         # [ ] Usage & installation docs (Phase 5)
├── requirements.txt                  # [x] Pinned dependencies (for pip; to do: just list actually used by the software)
├── requirements-dev.txt              # [ ] To Do (not existing yet)
├── run.sh                            # [x] Launcher script for Telegram poller
├── src
│   ├── __init__.py
│   └── llm_telegram_bot
│       ├── char_loader.py            # [x] Load/validate character YAMLs (Phase 3)
│       ├── commands
│       │   ├── commands_loader.py    # [x] YAML → CommandInfo objects
│       │   ├── commands_registry.py  # [x] Decorator & registry for handlers
│       │   ├── handlers
│       │   │   ├── bot.py            # [x] `/bot` handler
│       │   │   ├── bots.py           # [x] `/bots` handler
│       │   │   ├── char.py           # [x] `/char` handler (Phase 3)
│       │   │   ├── chars.py          # [x] `/chars` alias (Phase 3)
│       │   │   ├── defaults.py       # [ ] `/defaults` (Phase 6)
│       │   │   ├── help.py           # [x] `/help` handler
│       │   │   ├── history.py        # [ ] `/history` (Phase 3)
│       │   │   ├── __init__.py
│       │   │   ├── jb.py             # [ ] `/jb` (Phase 6; automatic jailbreak prompts)
│       │   │   ├── memory.py         # [ ] `/memory` (Phase 3)
│       │   │   ├── model.py          # [x] `/model` handler
│       │   │   ├── models.py         # [x] `/models` handler
│       │   │   ├── reset.py          # [ ] `/reset` handler (reset to factory defaults)
│       │   │   ├── savelastprompt.py # [x] `/slp` handler
│       │   │   ├── savelastresponse.py # [x] `/slr` handler
│       │   │   ├── savestring.py     # [x] `/sstr` handler
│       │   │   ├── service.py        # [x] `/service` handler
│       │   │   ├── setdefaults.py    # [ ] `/setdefaults` (Phase 6)
│       │   │   ├── start.py          # [x] `/start` alias for `/bot`
│       │   │   ├── status.py         # [x] `/status` handler
│       │   │   ├── temperature.py    # [x] `/temp` handler
│       │   │   ├── tokens.py         # [x] `/tokens` handler
│       │   │   └── undo.py           # [ ] `/undo` (Phase 3/6)
│       │   └── parser.py             # [x] Parses incoming text → command+args
│       ├── config
│       │   ├── config_loader.py      # [x] Loads & validates config (refactored)
│       │   ├── __init__.py
│       │   └── schemas.py            # [x] Pydantic schemas for config validation
│       ├── llm
│       │   ├── dispatcher.py         # [x] Dispatches to correct LLM service
│       │   └── __init__.py
│       ├── services
│       │   ├── __init__.py
│       │   ├── service_groq.py       # [x] Groq API integration
│       │   ├── service_mistral.py    # [x] Mistral API integration
│       │   └── services_base.py      # [x] Abstract BaseLLMService
│       ├── session
│       │   ├── __init__.py
│       │   └── session_manager.py    # [x] Per-bot session isolation & defaults
│       ├── telegram
│       │   ├── client.py             # [x] Raw Telegram API I/O
│       │   ├── __init__.py
│       │   ├── poller.py             # [x] Main loop, chunking & routing
│       │   └── routing.py            # [x] Routes commands → handlers
│       └── utils
│           ├── escape_html.py        # [x] HTML sanitizer
│           ├── escape_markdown.py    # [x] Markdown sanitizer
│           ├── __init__.py
│           ├── logger.py             # [ ] Log-format polish (Phase 4)
│           └── message_utils.py      # [x] Telegram message chunking
├── tests
│   ├── conftest.py                 # [x] Pytest fixtures & handler import hack
│   ├── functional                  # [ ] Functional tests (Phase 1–3)
│   ├── helpers
│   │   └── command_utils.py        # [x] Test helpers for commands
│   ├── integration
│   │   ├── test_llm_services.py    # [ ] LLM dispatch & mock services
│   │   └── test_telegram_client.py # [x] TelegramClient I/O tests
│   ├── mocks                       # [ ] Test mocks (CLI, LLM)
│   ├── pytest.ini                  # [x] Pytest configuration
│   └── unit
│       ├── test_char_loader.py     # [ ] Phase 3
│       ├── test_commands.py        # [ ] Uncovered handlers
│       ├── test_config_loader.py   # [x] Config loader validation
│       ├── test_models_info_schema.py # [x] Models_info schema tests
│       └── test_routing.py         # [x] Routing edge-case tests
└── tmp                             # [x] Temporary files & downloads
```

DEPRECATION: docopt is being installed using the legacy 'setup.py install' method, because it does not have a 'pyproject.toml' and the 'wheel' package is not installed. pip 23.1 will enforce this behaviour change. A possible replacement is to enable the '--use-pep517' option. Discussion can be found at https://github.com/pypa/pip/issues/8559
Running setup.py install for docopt ... done
DEPRECATION: langdetect is being installed using the legacy 'setup.py install' method, because it does not have a 'pyproject.toml' and the 'wheel' package is not installed. pip 23.1 will enforce this behaviour change. A possible replacement is to enable the '--use-pep517' option. Discussion can be found at https://github.com/pypa/pip/issues/8559
Running setup.py install for langdetect ... done
DEPRECATION: breadability is being installed using the legacy 'setup.py install' method, because it does not have a 'pyproject.toml' and the 'wheel' package is not installed. pip 23.1 will enforce this behaviour change. A possible replacement is to enable the '--use-pep517' option. Discussion can be found at https://github.com/pypa/pip/issues/8559

- python3 -m spacy download de_core_news_sm
- python3 -m spacy download de_core_news_md
- python3 -m spacy download en_core_web_sm

