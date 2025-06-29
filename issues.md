# Project Roadmap (Updated 2025-05-20)

## Fixes

- [ ] update templates of configuration files.
- [ ] create **CLI runner** (bin/cli-chatbot.py) with Markdown rendering
- [ ] test chutes models (e.g. DeepSeek R1 0528 models are not working [?])
- [ ] when dropping a user or char via `/user drop` or `/char drop`, messages are (probably) flushed to correct history but not removed from HistoryManager.
- [ ] sent pictures are not correctly saved to disk

## Phase 0 – Development Infrastructure & CI

- [ ] Add & configure pre-commit hooks (black, isort, flake8, mypy)
- [ ] Enforce mypy typing on all public interfaces
- [ ] Create `requirement.txt` and `requirements-dev.txt`
- [ ] `pip install pipreqs pip-audit renovate`, `pipreqs src --force --ignore ../.venv --savepath requirements.txt`
- [ ] Create a lightweight CI pipeline to run pre-commit, pytest, mypy
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

## Phase 4 – Memory Module via History Summarization (🟡 In Progress)

### 4.1 Tier-0 “Just-In-Time” Compression

- [x] if message > T0_cap, call `safe_summarize(..., sentences=T0_cap/avg)`

### 4.2 Tier-1 Promotion

- [x] When `len(tier0)>N0`, pop oldest, summarize to ≤ T1_cap tokens, wrap in `Summary`
- [x] `Summary` now carries `ts`, `who`, `text`, `tokens`

### 4.3 Tier-2 Rolling “Mega” Summaries

- [x] When `len(tier1)>N1`, batch a fraction (25% of N1) or up to `K`, combine, prepend previous mega
- [x] Extract detecting-language, steering prompt, `safe_summarize(..., sentences=MEGA_SENTENCES)`
- [x] Extract & merge NER keywords for English and German (limit to `MAX_KEYWORDS`)

### 4.4 Nice-to-Have: Time Awareness

- [x] Before `[PROMPT]`, inject a small block: `[CONTEXT]`: `Last message at {last_msg.ts} by {last_msg.who}. Current time is {now} to provide Weekday and Time of Day
- [x] Support Jinja in user config to adapt replies if gap of >2h
- [x] Support Jinja in user templates for time-aware behavior

### 4.5 Prompt Assembly & Injection

- [x] build_full_prompt() order:
  1. `[SYSTEM]`
  2. `[START OF THE CONVERSATION]` → tier2.megas
  3. `[EARLY SUMMARY]` → tier1
  4. `[RECENT CONVERSATION]` → tier0 (use `msg.compressed`)
  5. `[CONTEXT]` (timestamps & “last at) (s. below)
  6. `[PROMPT]` → user text
- [ ] switch syntax to `< system >` ... `</ system >`?

## Phase 5 – Configuration & Tuning

- [x] create command `think on|off` to turn on / off showing think blocks
- [ ] Maybe, switch to topic modeling for tier2 with updated weights such that old topics fade
- [ ] Move parameters for summary (e.g., `N0`, `N1`, `K`, `T0_cap`, `T1_cap`, `T2_cap`) into `config.yaml` per-bot
- [ ] Read parameters at startup and pass into `HistoryManager`
- [ ] Expose `/sum [params]` to tweak summarization on the fly
- [ ] `/dlm`: delete the last message in the history buffer and HistoryManager

## Phase 6 – Logging, Formatting & CLI 🟡

- [x] Enhanced send_message logs (chat_id, duration, preview)
- [x] HTML‐safe escapes for all outgoing messages
- [x] telegram_splitter.py for Telegram’s 4096-char limit
- [ ] Update README.md with examples

## Phase 7 – Mid-Term & Testing

- [ ] Add unit tests for each tier’s summarization logic & metrics (token savings)
- [ ] Implement CI “smoke test”: Telegram → LLM end-to-end
- [ ] Auto-reload tier1/tier2 on startup if file exists (however, computational load is not that high to summarize again)
- [ ] "finalize" `run.sh`

## Phase 8 – Nice-to-Have Commands

- [ ] `/undo`, `/reset`, `/defaults`, `/jb` (auto jailbreaks)
- [ ] `/memory` to inspect current tiers
- [ ] Implement more services ([s. Free LLM resources](https://github.com/cheahjs/free-llm-api-resources?tab=readme-ov-file))
- [ ] Implement other models: image analysis, text-to-speech, speech-to-text

## Out of scope at the moment

- use graph database to improve memory / replies
- use langmem or mem0

## Project Structure & Status (Updated 2025-05-04)

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

## Notes for `run.sh`

DEPRECATION: docopt is being installed using the legacy 'setup.py install' method, because it does not have a 'pyproject.toml' and the 'wheel' package is not installed. pip 23.1 will enforce this behaviour change. A possible replacement is to enable the '--use-pep517' option. Discussion can be found at https://github.com/pypa/pip/issues/8559
Running setup.py install for docopt ... done
DEPRECATION: langdetect is being installed using the legacy 'setup.py install' method, because it does not have a 'pyproject.toml' and the 'wheel' package is not installed. pip 23.1 will enforce this behaviour change. A possible replacement is to enable the '--use-pep517' option. Discussion can be found at https://github.com/pypa/pip/issues/8559
Running setup.py install for langdetect ... done
DEPRECATION: breadability is being installed using the legacy 'setup.py install' method, because it does not have a 'pyproject.toml' and the 'wheel' package is not installed. pip 23.1 will enforce this behaviour change. A possible replacement is to enable the '--use-pep517' option. Discussion can be found at https://github.com/pypa/pip/issues/8559

```bash
python3 -m spacy download de_core_news_sm
python3 -m spacy download de_core_news_md
python3 -m spacy download en_core_web_sm
python3 -m spacy download en_core_web_md
```
