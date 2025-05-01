# src/telegram/client.py
"""
Telegram API Interface Layer

What It Does:
This file handles all communication with the Telegram API, making it a low-level
utility that:
    - Manages sessions with the Telegram server.
    - Handles incoming messages and file uploads (get_updates, get_file, download_file).
    - Sends text messages and error logs back to the user (send_message).
    - Manages a per-chat download folder and will also support saving chat history.

Integration Model:
This module does not interpret commands or respond to specific user intent
- it's strictly about I/O between Telegram and your application.
Other modules (like poller.py, routing.py, and parser.py) will import and use this client like so:

client = TelegramClient(...)
await client.send_message("Hi there!")
"""

import itertools
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

from src.utils.escape_markdown import safe_message
from src.utils.logger import logger


class TelegramClient:
    allowed_extensions: List[str] = [
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".webp",
        ".mp3",
        ".wav",
        ".ogg",
        ".m4a",
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".webm",
        ".zip",
        ".tar.gz",
        ".tar",
        ".gz",
    ]

    def __init__(
        self,
        token: str,
        chat_id: int,
        bot_name: str = "bot",
        download_path: str = "tmp",
        chat_history_path: str = "tmp",
    ):
        self.token = token
        self.bot_name = bot_name
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.download_base_url = f"https://api.telegram.org/file/bot{token}"

        # The session starts out None
        self.session: Optional[aiohttp.ClientSession] = None

        # Prepare download directory
        self.download_path = Path(download_path) / bot_name / str(chat_id)
        self.download_path.mkdir(parents=True, exist_ok=True)

        # Prepare chat history directory
        self.chat_history_path = Path(chat_history_path) / bot_name / str(chat_id)
        self.chat_history_path.mkdir(parents=True, exist_ok=True)

    async def init_session(self) -> None:
        """Create the aiohttp session."""
        self.session = aiohttp.ClientSession()

    async def close_session(self) -> None:
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def send_message(
        self,
        text: str,
        parse_mode: str = "MarkdownV2",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Send a text message to the configured chat, escaping for the chosen parse_mode."""
        if self.session is None:
            await self.init_session()
        session: aiohttp.ClientSession = self.session  # type: ignore[assignment]

        if parse_mode == "MarkdownV2":
            # escape everything so MarkdownV2 is valid
            clean = safe_message(text)

        elif parse_mode == "HTML":
            # assume your handler has already produced valid HTML tags
            clean = text

        else:
            clean = text

        payload: Dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": clean,
            "parse_mode": parse_mode,
            **kwargs,  # e.g. disable_web_page_preview=True, reply_markup=…
        }

        start = time.time()
        try:
            async with session.post(f"{self.api_url}/sendMessage", data=payload) as resp:
                data = await resp.json()
                elapsed = time.time() - start

                if resp.status == 200 and data.get("ok", False):
                    logger.debug(f"[send_message] Sent to {self.chat_id} in {elapsed:.2f}s: {clean!r}")
                    return data
                else:
                    error = data.get("description", f"HTTP {resp.status}")
                    logger.error(f"[send_message] Failed ({elapsed:.2f}s): {error}")
                    return {
                        "ok": False,
                        "error_code": resp.status,
                        "description": error,
                    }
        except Exception as e:
            logger.exception(f"[send_message] Exception after {time.time() - start:.2f}s")
            return {"ok": False, "error_code": 500, "description": str(e)}

    async def get_updates(self, offset: Optional[int] = None) -> Dict[str, Any]:
        """Long-poll Telegram for new updates."""
        # Ensure session is initialized, then narrow type for MyPy
        if self.session is None:
            await self.init_session()
        session: aiohttp.ClientSession = self.session  # type: ignore[assignment]

        params: Dict[str, Any] = {}
        if offset is not None:
            params["offset"] = offset

        start = time.time()
        try:
            async with session.get(f"{self.api_url}/getUpdates", params=params) as resp:
                data = await resp.json()
                elapsed = time.time() - start

                if resp.status == 200 and data.get("ok", False):
                    # logger.debug(
                    #     f"[get_updates] Retrieved {len(data.get('result', []))} updates in {elapsed:.2f}s"
                    # )
                    return data
                else:
                    error = data.get("description", f"HTTP {resp.status}")
                    logger.error(f"[get_updates] Failed ({elapsed:.2f}s): {error}")
                    return {
                        "ok": False,
                        "error_code": resp.status,
                        "description": error,
                    }
        except Exception as e:
            logger.exception(f"[get_updates] Exception after {time.time() - start:.2f}s")
            return {"ok": False, "error_code": 500, "description": str(e)}

    async def get_file(self, file_id: str) -> Dict[str, Any]:
        """Fetch file metadata (including file_path) from Telegram."""
        # Ensure session is initialized, then narrow type for MyPy
        if self.session is None:
            await self.init_session()
        session: aiohttp.ClientSession = self.session  # type: ignore[assignment]

        logger.debug(f"[get_file] Requesting details for file_id={file_id}")
        start = time.time()
        try:
            async with session.post(f"{self.api_url}/getFile", data={"file_id": file_id}) as resp:
                data = await resp.json()
                elapsed = time.time() - start

                if resp.status == 200 and data.get("ok", False):
                    logger.debug(f"[get_file] Received in {elapsed:.2f}s: {data}")
                    return data
                else:
                    error = data.get("description", f"HTTP {resp.status}")
                    logger.error(f"[get_file] Failed ({elapsed:.2f}s): {error}")
                    await self.send_message(f"⚠️ Could not retrieve file info: {error}")
                    return {
                        "ok": False,
                        "error_code": resp.status,
                        "description": error,
                    }
        except Exception as e:
            logger.exception(f"[get_file] Exception after {time.time() - start:.2f}s")
            await self.send_message(f"❌ Exception retrieving file info: {e}")
            return {"ok": False, "error_code": 500, "description": str(e)}

    async def download_file(self, file_path: str, original_name: str | None = None) -> Dict[str, Any]:
        """Download a file by its Telegram file_path and save it with a unique name (preserving original if possible)."""
        # Ensure session is initialized
        if self.session is None:
            await self.init_session()
        session: aiohttp.ClientSession = self.session  # type: ignore[assignment]

        url = f"{self.download_base_url}/{file_path}"
        safe_name = original_name or os.path.basename(file_path)
        destination = self.download_path / safe_name

        # Ensure destination filename is unique
        if destination.exists():
            base, ext = os.path.splitext(safe_name)
            for i in itertools.count(1):
                alt_name = f"{base}_{i}{ext}"
                alt_path = self.download_path / alt_name
                if not alt_path.exists():
                    destination = alt_path
                    break

        logger.debug(f"[download_file] URL={url}, dest={destination}")
        start = time.time()
        try:
            async with session.get(url) as resp:
                elapsed = time.time() - start
                if resp.status == 200:
                    content = await resp.read()
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with open(destination, "wb") as f:
                        f.write(content)
                    logger.info(f"[download_file] Saved {destination.name} ({len(content)} bytes) in {elapsed:.2f}s")
                    await self.send_message(f"✅ Downloaded {destination.name}")
                    return {"ok": True, "file_name": str(destination)}
                else:
                    error = f"HTTP {resp.status}"
                    logger.error(f"[download_file] Failed ({elapsed:.2f}s): {error}")
                    await self.send_message(f"❌ Download failed: {error}")
                    return {
                        "ok": False,
                        "error_code": resp.status,
                        "description": error,
                    }
        except Exception as e:
            logger.exception(f"[download_file] Exception after {time.time() - start:.2f}s")
            await self.send_message(f"❌ Exception downloading file: {e}")
            return {"ok": False, "error_code": 500, "description": str(e)}
