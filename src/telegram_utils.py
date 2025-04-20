import json
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml

# --- Config paths ---
BASE_DIR = Path(__file__).resolve().parent
CONFIG_YAML = (BASE_DIR / "../config/config.yaml").resolve()
MODELS_JSON = (BASE_DIR / "../config/models_info.json").resolve()
COMMANDS_YAML = (BASE_DIR / "../config/commands.yaml").resolve()


# --- Utility functions ---
def load_yaml(path: Path) -> dict:
    """Load a YAML file and return its contents as a dictionary."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_json(path: Path) -> dict:
    """Load a JSON file and return its contents as a dictionary."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f) or {}


# --- Telegram API helpers ---
def get_updates(token: str, offset: int = None, timeout: int = 10) -> list:
    """Retrieve updates/messages from Telegram for the given bot token."""
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    resp = requests.get(url, params=params, timeout=timeout + 30)
    resp.raise_for_status()
    return resp.json().get("result", [])


def send_message(
    token: str, chat_id: int, text: str, parse_mode: str = "Markdown"
) -> None:
    """Send a message to a specific chat via Telegram API."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    try:
        requests.post(url, json=payload, timeout=60).raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] Telegram send_message failed: {e}")


def send_startup_message(bot_token, chat_id, service, model, temperature, max_tokens):
    """Send a startup message to a given Telegram chat."""
    msg = (
        f"🤖 Bot started\n"
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"🔌 Service: {service}\n"
        f"🧠 Model: {model}\n"
        f"🌡️ Temperature: {temperature}\n"
        f"🔢 Max Tokens: {max_tokens}\n"
        f'ℹ️ Send "/help" for help'
    )
    send_message(bot_token, chat_id, msg)


# --- LLM API helpers ---
def get_service_conf(config: dict, service_name: str) -> tuple[str, str]:
    """Return (endpoint, API key) for a given service from config."""
    svc = config.get("services", {}).get(service_name)
    if not svc or not svc.get("enabled", False):
        raise ValueError(f"Service '{service_name}' not found or not enabled.")
    api_key = svc.get("api_key") or svc.get("apy_key")  # fallback typo check
    if not api_key:
        raise ValueError(f"API key missing for service '{service_name}'.")
    return svc["endpoint"], api_key


# --- Load command specs from YAML ---
COMMAND_SPECS = load_yaml(COMMANDS_YAML)


def _make_help_text() -> str:
    """Build and return help text for all available commands."""
    lines = ["📚 Available commands:"]
    for name, spec in COMMAND_SPECS.items():
        lines.append(f"{spec['usage']} – {spec['description']}")
    return "\n".join(lines)


# --- Command registry: cmd -> handler method name in ChatSession ---
COMMAND_REGISTRY = {
    "help": ("_cmd_help", None),
    "showsettings": ("_cmd_showsettings", None),
    "services": ("_cmd_services", None),
    "models": ("_cmd_models", None),
    "model": ("_cmd_model", None),
    "cservice": ("_cmd_cservice", None),
    "cmodel": ("_cmd_cmodel", None),
    "temperature": ("_cmd_temperature", None),
    "maxtokens": ("_cmd_maxtokens", None),
    "setasdefaults": ("_cmd_setasdefaults", None),
    "factoryreset": ("_cmd_factoryreset", None),
}


class ChatSession:
    def __init__(self, config: dict, models_info: dict):
        default = config.get("default", {})
        tel_cfg = config.get("telegram", {})

        self.config = config
        self.models_info = models_info
        # TO DO: use the defaults in CONFIG_YAML 
        self.service = default.get("service")
        self.model = default.get("model")
        self.temperature = tel_cfg.get("default_temperature", 0.7)
        self.max_tokens = tel_cfg.get("default_max_tokens", 100)

        self.bot_token = tel_cfg.get("bot_token")
        self.allowed_users = set(tel_cfg.get("chat_id", []))

        self.poll_idle = tel_cfg.get("polling_interval_idle", 60)
        self.poll_active = tel_cfg.get("polling_interval_active", 5)
        self.interval = self.poll_idle
        self.last_active = None
        self.offset = None

    # ——— Command handlers ———
    def _cmd_help(self, arg: str) -> str:
        return _make_help_text()

    def _cmd_showsettings(self, arg: str) -> str:
        return (
            f"Current settings:\n"
            f"- Service: {self.service}\n"
            f"- Model: {self.model}\n"
            f"- Temperature: {self.temperature}\n"
            f"- Max Tokens: {self.max_tokens}"
        )

    def _cmd_services(self, arg: str) -> str:
        return "Available services:\n" + "\n".join(self.config.get("services", {}))

    def _cmd_models(self, arg: str) -> str:
        svc_models = self.models_info.get(self.service, {})
        if not svc_models:
            return f"No models for '{self.service}'."
        return "\n".join(svc_models)

    def _cmd_model(self, arg: str) -> str:
        return self.model_info(arg)

    def _cmd_cservice(self, arg: str) -> str:
        if not arg:
            return f"Usage: {COMMAND_SPECS['cservice']['usage']}"
        if arg not in self.config.get("services", {}):
            return f"❌ Service '{arg}' not found.\n\n" + self._cmd_services("")
        self.service = arg
        default_model = self.config["services"][arg].get("model")
        if default_model:
            self.model = default_model
        return f"Service set to '{self.service}'"

    def _cmd_cmodel(self, arg: str) -> str:
        if not arg:
            return f"Usage: {COMMAND_SPECS['cmodel']['usage']}"
        if arg not in self.models_info.get(self.service, {}):
            return f"❌ Model '{arg}' not found in '{self.service}'."
        self.model = arg
        return f"Model set to '{self.model}'"

    def _cmd_temperature(self, arg: str) -> str:
        try:
            t = float(arg)
            if not (0 <= t <= 2):
                raise ValueError
            self.temperature = t
            return f"Temperature set to {t}"
        except:
            return f"Usage: {COMMAND_SPECS['temperature']['usage']}"

    def _cmd_maxtokens(self, arg: str) -> str:
        try:
            m = int(arg)
            if m <= 0:
                raise ValueError
            self.max_tokens = m
            return f"Max tokens set to {m}"
        except:
            return f"Usage: {COMMAND_SPECS['maxtokens']['usage']}"

    def _cmd_setasdefaults(self, arg: str) -> str:
        try:
            cfg = load_yaml(Path(self.config["_source_path"]))  # store path
            cfg.setdefault("default", {})
            cfg["default"].update(
                {
                    "service": self.service,
                    "model": self.model,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                }
            )
            with open(self.config["_source_path"], "w", encoding="utf-8") as f:
                yaml.safe_dump(cfg, f, sort_keys=False)
            return "Defaults saved ✅"
        except Exception as e:
            return f"[ERROR] {e}"

    def _cmd_factoryreset(self, arg: str) -> str:
        try:
            with open(CONFIG_YAML, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}

            # Get factory defaults from config or fallback
            factory_defaults = config_data.get(
                "factorydefaults",
                {
                    "service": "groq",
                    "model": "llama-3.3-70-versatile",
                    "temperature": 0.7,
                    "maxtoken": 4096,
                },
            )

            # Apply in-session values
            self.service = factory_defaults["service"]
            self.model = factory_defaults["model"]
            self.temperature = factory_defaults["temperature"]
            self.max_tokens = factory_defaults["maxtoken"]

            # Ensure config is updated with factorydefaults block
            config_data["factorydefaults"] = factory_defaults

            with open(CONFIG_YAML, "w", encoding="utf-8") as f:
                yaml.safe_dump(config_data, f, sort_keys=False)

            self.save_defaults()  # Also persist these as the new defaults
            return "Bot and defaults set to factory settings ✅"

        except Exception as e:
            return f"[ERROR] Factory reset failed: {e}"

    # ——— Dispatch & processing ———

    def handle_command(self, text: str) -> str:
        pats = text.lstrip("/").split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        entry = COMMAND_REGISTRY.get(cmd)
        if not entry:
            return f"Unknown command: /{cmd}. Use /help"
        handler_name, _ = entry
        return getattr(self, handler_name)(arg)

    def model_info(self, model_name: str = "") -> str:
        svc_models = self.models_info.get(self.service, {})
        target_model = model_name.strip() or self.model

        info = svc_models.get(target_model)
        if not info:
            return f"Model '{target_model}' not found for service '{self.service}'."

        # Extract fields with defaults
        release_year = info.get("release_year", "N/A")
        token_win = info.get("token_win", [])
        token_str = f"{token_win[0]}-{token_win[1]}" if len(token_win) == 2 else "N/A"
        rank_power = info.get("rank_power", "N/A")
        rank_coding = info.get("rank_coding", "N/A")
        rank_jail = info.get("rank_jail", "N/A")
        purpose = info.get("main_purpose", "N/A")
        strengths = info.get("strengths", "N/A")
        weaknesses = info.get("weaknesses", "N/A")
        details = info.get("details", "N/A")
        jailbreaks = info.get("jailbreaks", [])

        # Build output
        lines = [
            f"*{target_model}*",
            f"by {self.service} ({release_year})\n",
            f"*{token_str}k tokens for*: {purpose}\n",
            f"*Power:* {rank_power}",
            f"*Coding:* {rank_coding}",
            f"*Jailbreak:* {rank_jail}\n",
            f"+ {strengths}",
            f"- {weaknesses}\n",
            f"{details}",
        ]
        for jb in jailbreaks:
            lines.append(f"- {jb}")

        return "\n".join(lines)

    def list_models(self) -> str:
        svc_models = self.models_info.get(self.service, {})
        if not svc_models:
            return f"No models found for service '{self.service}'."

        lines = [f"*Models for {self.service}*:"]
        for name, info in svc_models.items():
            year = info.get("release_year", "N/A")
            win = info.get("token_win", [])
            token_str = f"{win[0]}-{win[1]}" if len(win) == 2 else "N/A"
            p = info.get("rank_power", "N/A")
            c = info.get("rank_coding", "N/A")
            j = info.get("rank_jail", "N/A")

            lines.append(f"\n*{name}* ({year})")
            lines.append(f"*Tokens:* {token_str}")
            lines.append(f"*Power*: {p}, *Coding*: {c}, *JB:* {j}")

        return "\n".join(lines)

    def process_update(self, update: dict) -> None:
        msg = update.get("message")
        if not msg:
            return

        user_id = msg.get("from", {}).get("id")
        if self.allowed_users and user_id not in self.allowed_users:
            return

        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        self.last_active = datetime.now()
        self.interval = self.poll_active

        if text.startswith("/"):
            reply = self.handle_command(text)
        else:
            try:
                endpoint, api_key = get_service_conf(self.config, self.service)
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": text}],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                }
                resp = requests.post(
                    endpoint,
                    json=payload,
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=60,
                )
                resp.raise_for_status()
                reply = resp.json()["choices"][0]["message"]["content"]

            except Exception as e:
                reply = f"API Error: {e}"

        send_message(self.bot_token, chat_id, reply)

    def run(self) -> None:
        while True:
            updates = get_updates(
                self.bot_token, offset=self.offset, timeout=self.interval
            )
            if updates:
                for upd in updates:
                    self.process_update(upd)
                    self.offset = upd["update_id"] + 1
            else:
                if self.last_active:
                    self.interval = min(self.poll_idle, self.interval * 2)

            time.sleep(1)


def main():
    # 1) Load raw dicts
    cfg: dict = load_yaml(CONFIG_YAML)
    cfg["_source_path"] = str(CONFIG_YAML)  # So handlers know where to write
    models: dict = load_json(MODELS_JSON)

    # 2) Create and run session
    session = ChatSession(cfg, models)
    send_startup_message(
        session.bot_token,
        next(iter(session.allowed_users), 0),
        session.service,
        session.model,
        session.temperature,
        session.max_tokens,
    )
    session.run()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    main()
