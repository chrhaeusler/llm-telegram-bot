import json
import signal
import sys
import time
from datetime import datetime

import requests
import yaml

# Graceful exit on Ctrl+C
signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))


# --- Utility functions ---
def load_yaml(path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_models_info(path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# --- Telegram API helpers ---
def get_updates(token: str, offset: int = None, timeout: int = 10) -> list:
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    response = requests.get(url, params=params, timeout=timeout + 30)
    response.raise_for_status()
    return response.json().get("result", [])


def send_message(
    token: str, chat_id: int, text: str, parse_mode: str = "Markdown"
) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] Telegram send_message failed: {e}")


def send_startup_message(bot_token, chat_id, service, model, temperature, max_tokens):
    startup_message = (
        f"Bot started\n"
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"Service: {service}\n"
        f"Model: {model}\n"
        f"Temperature: {temperature}\n"
        f"Max Tokens: {max_tokens}\n"
        f'Send "/help" for help'
    )
    send_message(bot_token, chat_id, startup_message)


# --- LLM API helpers ---
def get_service_conf(config: dict, service_name: str) -> tuple:
    svc = config.get("services", {}).get(service_name)
    if not svc or not svc.get("enabled", False):
        raise ValueError(f"Service '{service_name}' not found or not enabled.")
    api_key = svc.get("api_key") or svc.get("apy_key")
    if not api_key:
        raise ValueError(f"API key missing for service '{service_name}'.")
    return svc["endpoint"], api_key


# --- Chat session class ---
class ChatSession:
    def __init__(self, cfg: dict, models_info: dict):
        default = cfg.get("default", {})
        tel_cfg = cfg.get("telegram", {})

        self.config = cfg
        self.models_info = models_info

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

    # def list_services(self) -> str:
    #     return "Available services:\n" + "\n".join(
    #         self.config.get("services", {}).keys()
    #     )

    # def list_models(self) -> str:
    #     svc_models = self.models_info.get(self.service, {})
    #     if not svc_models:
    #         return f"No models found for service '{self.service}'."

    #     lines = [f"*Models for {self.service}*:\n"]
    #     for name, info in svc_models.items():
    #         lines.append(f"*{name}*")
    #         lines.append(info.get("short", "No short description available."))
    #         lines.append(f"*Strengths:* {info.get('strengths', 'N/A')}")
    #         lines.append(f"*Weaknesses:* {info.get('weaknesses', 'N/A')}")

    #     return "\n".join(lines).rstrip()

    def list_models(self) -> str:
        svc_models = self.models_info.get(self.service, {})
        if not svc_models:
            return f"No models found for service '{self.service}'."
        
        def fmt_tokens(n):
            return f"{n//1000}k" if n >= 1000 else str(n)

        lines = [f"*Models for {self.service}*:"]
        for name, info in svc_models.items():
            # release year
            year = info.get("release_year", "N/A")

            # token window
            win = info.get("token_win", [])
            token_str = f"{win[0]}-{win[1]}" if len(win) == 2 else "N/A"

            # ranks
            p = info.get("rank_power", "N/A")
            c = info.get("rank_coding", "N/A")
            j = info.get("rank_jail", "N/A")

            # create output
            lines.append(f"\n*{name}* ({year})")
            lines.append(f"*Tokens:* {token_str}")
            lines.append(f"*Powwer*: {p}, *Coding*: {c}, *JB:* {j}")
        return "\n".join(lines)


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

    def save_defaults(self, path: str = "config/config.yaml") -> str:
        """Write current service, model, temperature, and max_tokens to the default block in config.yaml."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)

            # Update the default section
            cfg.setdefault("default", {})
            cfg["default"]["service"] = self.service
            cfg["default"]["model"] = self.model
            cfg["default"]["temperature"] = self.temperature
            cfg["default"]["maxtoken"] = self.max_tokens

            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump(cfg, f, sort_keys=False)

            return "Defaults saved to config.yaml ✅"
        except Exception as e:
            return f"[ERROR] Failed to write config.yaml: {e}"

    def factory_reset(self):
        factory_defaults = {
            "service": "mistral",
            "model": "mistral-small-latest",
            "temperature": 0.7,
            "maxtoken": 100,
        }

        # Set active in-session values
        self.service = factory_defaults["service"]
        self.model = factory_defaults["model"]
        self.temperature = factory_defaults["temperature"]
        self.max_tokens = factory_defaults["maxtoken"]

        # Overwrite the YAML config file
        try:
            with open("config/config.yaml", "r") as f:
                config_data = yaml.safe_load(f) or {}

            config_data["factorydefaults"] = factory_defaults

            with open("config/config.yaml", "w") as f:
                yaml.safe_dump(config_data, f, sort_keys=False)

                self.service = "mistral"
                self.model = "mistral-small-latest"
                self.temperature = 0.7
                self.max_tokens = 100
                self.save_defaults()  # Also persist these as the new defaults
                return "Bot and defaults set to factory settings"

            return "Factory reset complete. All settings restored to defaults."
        except Exception as e:
            return f"Factory reset failed: {str(e)}"

    def handle_command(self, text: str) -> str:
        parts = text.lstrip("/").split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "help":
            return (
                "Available commands:\n"
                "/help – Show this message\n"
                "/showsettings - Show service, model, temperature & max tokens\n"
                "/services – List available services\n"
                "/cservice <name> – Change service (e.g. mistral or groq)\n"
                "/models – List models for current service\n"
                "/cmodel <name> – Change model of current service\n"
                "/temperature <float> - Change model's temperature\n"
                "/maxtokens <int> - Change max token\n"
                "/setasdefaults - Set current settings as default\n"
                "/factoryreset - Reset to factory defaults"
            )

        elif cmd == "services":
            return self.list_services()

        elif cmd == "cservice":
            if not arg:
                return "Usage: /cservice <service name>"
            if arg not in self.config.get("services", {}):
                return f"Service '{arg}' not found."
            if not self.config["services"][arg].get("enabled", False):
                return f"Service '{arg}' is not enabled."
            self.service = arg
            self.model = self.config["services"][arg]["model"]
            return f"Service switched to '{self.service}', using model '{self.model}'"

        elif cmd == "models":
            return self.list_models()

        elif cmd == "model":
            return self.model_info(arg)

        elif cmd == "cmodel":
            if not arg:
                return "Usage: /cmodel <model name>"
            if arg not in self.models_info.get(self.service, {}):
                return f"Model '{arg}' not found in service '{self.service}'."
            self.model = arg
            return f"Model switched to '{self.model}'"

        elif cmd == "temperature":
            try:
                new_temp = float(arg)
                if not (0 <= new_temp <= 2):
                    return "Temperature must be between 0.0 and 2.0"
                self.temperature = new_temp
                return f"Temperature set to {new_temp}"
            except ValueError:
                return "Usage: /temperature <float> (e.g. /temperature 0.7)"

        elif cmd == "maxtokens":
            try:
                new_max = int(arg)
                if new_max <= 0:
                    return "Max tokens must be a positive integer"
                self.max_tokens = new_max
                return f"Max tokens set to {new_max}"
            except ValueError:
                return "Usage: /maxtokens <int> (e.g. /maxtokens 512)"
        # Write current service, model, temperature, and max_tokens to
        # the default block in config.yaml.
        elif cmd == "setasdefaults":
            return self.save_defaults()

        elif cmd == "showsettings":
            return (
                f"Current settings:\n"
                f"- Service: {self.service}\n"
                f"- Model: {self.model}\n"
                f"- Temperature: {self.temperature}\n"
                f"- Max Tokens: {self.max_tokens}"
            )

        elif cmd == "factoryreset":
            return self.factory_reset()
        else:
            return f"Unknown command: /{cmd}. Use /help to list available commands."

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
            time.sleep(0)
