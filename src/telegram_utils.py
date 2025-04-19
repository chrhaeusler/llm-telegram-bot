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
    """Load and return the YAML configuration from given path."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_models_info(path) -> dict:
    """Load and return the models info JSON from given path."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# --- Telegram API helpers ---
def get_updates(token: str, offset: int = None, timeout: int = 0) -> list:
    """Poll Telegram getUpdates endpoint and return update list."""
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    response = requests.get(url, params=params, timeout=timeout + 5)
    response.raise_for_status()
    return response.json().get("result", [])


def send_message(token: str, chat_id: int, text: str) -> None:
    """Send a text message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] Telegram send_message failed: {e}")


# --- LLM API proxy functions ---
def get_service_conf(config: dict, service_name: str) -> tuple:
    """Return endpoint and api_key for a given service, or raise ValueError if unavailable."""
    svc = config.get("services", {}).get(service_name)
    if not svc or not svc.get("enabled", False):
        raise ValueError(f"Service '{service_name}' not found or not enabled.")
    api_key = svc.get("api_key") or svc.get("apy_key")
    if not api_key:
        raise ValueError(f"API key missing for service '{service_name}'.")
    return svc["endpoint"], api_key


# --- Chat session state ---
class ChatSession:
    """
    Manages chat state, user commands, and proxies messages to the LLM service.
    """

    def __init__(self, cfg: dict, models_info: dict):
        # Load defaults from config
        default = cfg.get("default", {})
        tel_cfg = cfg.get("telegram", {})

        self.config = cfg
        self.models_info = models_info

        # Session parameters
        self.service = default.get("service")
        self.model = default.get("model")
        self.temperature = tel_cfg.get("default_temperature", 0.7)
        self.max_tokens = tel_cfg.get("default_max_tokens", 100)

        # Telegram settings
        self.bot_token = tel_cfg.get("bot_token")
        self.allowed_users = set(tel_cfg.get("allowed_user_ids", []))

        # Polling intervals
        self.poll_idle = tel_cfg.get("polling_interval_idle", 60)
        self.poll_active = tel_cfg.get("polling_interval_active", 5)
        self.interval = self.poll_idle
        self.last_active = None
        self.offset = None

    def list_services(self) -> str:
        """List all available services, one per line."""
        return "\n".join(self.config.get("services", {}).keys())

    def list_models(self) -> str:
        """List models for current service with 'censored' status and short description."""
        svc_models = self.models_info.get(self.service, {})
        lines = []
        for name, info in svc_models.items():
            cens_status = info.get("censored", "unknown")
            lines.append(f"{name} ({cens_status}): {info.get('short')}")
        # Double newline after listing
        return "\n".join(lines) + "\n\n"

    def model_info(self, model_name: str) -> str:
        """Return detailed info for a model, or list available models if no name given."""
        svc_models = self.models_info.get(self.service, {})
        if not model_name:
            # No model specified: list all model names
            return "\n".join(svc_models.keys())
        info = svc_models.get(model_name)
        if not info:
            return f"Model '{model_name}' not found for service '{self.service}'."
        return (
            f"Creator: {info.get('creator')}\n"
            f"{info.get('censored')}\n"
            f"Strengths: {info.get('strengths')}\n"
            f"Weaknesses: {info.get('weaknesses')}\n"
            f"Details: {info.get('details')}"
        )

    def handle_command(self, text: str) -> str:
        """Parse and execute slash commands, returning a reply string."""
        parts = text.lstrip("/").split(maxsplit=1)
        cmd = parts[0]
        arg = parts[1].strip() if len(parts) > 1 else ""
        # Command handling logic...
        return None

    def process_update(self, update: dict) -> None:
        """Process a single Telegram update: handle commands or chat messages."""
        msg = update.get("message")
        if not msg:
            return
        user_id = msg.get("from", {}).get("id")
        if self.allowed_users and user_id not in self.allowed_users:
            return
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        # Reset backoff on activity
        self.last_active = datetime.utcnow()
        self.interval = self.poll_active

        # Check if it's a command
        if text.startswith("/"):
            reply = self.handle_command(text)
        else:
            # Regular chat message: proxy to LLM
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
                    timeout=20,
                )
                resp.raise_for_status()
                reply = resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                reply = f"API Error: {e}"

        send_message(self.bot_token, chat_id, reply)

    def run(self) -> None:
        """Main loop: poll for updates and process each one, with backoff."""
        while True:
            updates = get_updates(
                self.bot_token, offset=self.offset, timeout=self.interval
            )
            if updates:
                for upd in updates:
                    self.process_update(upd)
                    self.offset = upd["update_id"] + 1
            else:
                # No updates: exponential backoff towards idle interval
                if self.last_active:
                    self.interval = min(self.poll_idle, self.interval * 2)

            time.sleep(0)
