# Project Structure & Status

```bash
├── bin
│   └── cli-chatbot.py                # [ ] CLI entrypoint (Phase 5) – stub, not implemented yet
├── config
│   ├── chars
│   │   ├── char_template.yaml        # [ ] Character YAML template (Phase 3)
│   │   └── lara-aimi-kimura.yaml     # [ ] Example character definition (Phase 3)
│   ├── commands.yaml                 # [x] Command definitions (used by `/help`, registry)
│   ├── config-template.yaml          # [ ] Template for config.yaml (needs update)
│   ├── config.yaml                   # [x] Active bot & LLM settings (loaded & validated)
│   ├── models_info.json              # [x] Model metadata (used by `/models`, `/model`)
│   └── users
│       └── user_template.yaml        # [ ] User profile YAML template (Phase 3)
├── issues.md                         # [ ] High-level issues & notes
├── LICENSE                           # [x] Project license
├── logs                              # [ ] Runtime logs (auto-generated)
├── poetry.lock                       # [x] Locked dependencies
├── pyproject.toml                    # [x] Project metadata & tools (poetry, black, ruff, mypy)
├── README.md                         # [ ] Usage & installation docs (Phase 5)
├── requirements.txt                  # [x] Pinned dependencies (for pip; to do: just list actually used by the software)
├── requirements-dev.txt              # [ ] To Do (not existing yet)
├── run.sh                            # [x] Launcher script for Telegram poller
├── src
│   ├── __init__.py
│   └── llm_telegram_bot
│       ├── char_loader.py            # [ ] Load/validate character YAMLs (Phase 3)
│       ├── commands
│       │   ├── commands_loader.py    # [x] YAML → CommandInfo objects
│       │   ├── commands_registry.py  # [x] Decorator & registry for handlers
│       │   ├── handlers
│       │   │   ├── bot.py            # [x] `/bot` handler
│       │   │   ├── bots.py           # [x] `/bots` handler
│       │   │   ├── char.py           # [ ] `/char` handler (Phase 3)
│       │   │   ├── chars.py          # [ ] `/chars` alias (Phase 3)
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
└── tmp                              # [x] Temporary files & downloads
```

# Roadmap (Updated 2025-05-03)

---

## Phase 0 – Development Infrastructure & CI

- [ ] Add & configure **pre-commit** hooks (black, isort, flake8, mypy).
- [ ] Add **mypy** typing to all public interfaces (session manager, routing, handlers).
- [ ] Create a lightweight **CI pipeline** (GitHub Actions / GitLab CI) to run:
  - pre-commit
  - pytest (unit + integration)
  - mypy
- [ ] Add CI status badges to README.

---

## Phase 1 – Core Foundations & “Simple” Commands ✅ *(done except tests)*

- [x] Ensure `src/commands/handlers/*.py` are imported in poller so `@register_command` runs.
- [x] Treat `/start` as alias for `/bot` in `routing.py`.

**Help & view commands:**
- [x] /help, /bots, /bot, /models, /status

**Set/override commands:**
- [x] /temp, /tokens, /service, /model

**File I/O commands:**
- [x] /savestr, /slp, /slr

**Unit tests:**
- [ ] For each handler: no-arg, valid-arg, invalid-arg.

---

## Phase 2 – Session Manager & State Isolation ✅ *(code complete)*

- [x] Refactored `session_manager.py` to:
  - Initialize default service/model
  - Accept bot identifier via parameter
  - Maintain per-bot, per-chat_id state
- [ ] Unit tests for all session state behaviors

---

## Phase 3 – Persona (Char/User) & Memory

- [ ] Abstract loader for character/user YAMLs
- [x] Implement `/char`, `/char list`, `/char <name>`
- [ ] /char reset
- [ ] Implement user_loader.py and /user commands
- [ ] /memory show/update/clear
- [ ] /history + /undo commands
- [ ] Integrate active character + memory into routing
- [ ] Unit tests for all commands

---

## Phase 4 – Logging & Formatting 🟡 *(in progress)*

- [ ] Enhance `send_message` logs (chat_id, duration, preview)
- [x] Use HTML formatting (escape utils in place)
- [x] Added `telegram_splitter.py` for 4096-char limit
- [ ] CLI-mode flag to skip HTML escapes

---

## Phase 5 – CLI Bot & Documentation 🟡 *(just started)*

- [x] Add `run.sh` launcher to project root
- [ ] Build CLI runner (mirror Telegram routing)
- [ ] Render Markdown/code blocks in terminal
- [ ] Update `README.md` with usage examples
- [ ] Add `docs/git-workflow.md`

---

## Phase 6 – Nice-to-Have Commands

- [ ] /jb (automatic jailbreak prompts)
- [ ] /setdefaults
- [ ] /defaults
- [ ] /reset (to factory defaults)
- [ ] Polish /undo
- [ ] Add more quality-of-life commands

---

## Phase 7 – Release Preparation

- [ ] CI green: pre-commit, pytest, mypy
- [ ] Smoke-tests: TelegramClient + LLM end-to-end
- [ ] Tag & publish v0.1-alpha
- [ ] Plan v0.2 (memory agents, DB, LangChain, etc.)
