# To Do:
# Sending messages to the chat seems broken
# I added comments above lines or block that raise an error
# is temperature implemented at all?
# implement startup message with, date time, bot, service, model, (max) token
# e.g. like this
# f"Bot started\n"
# f"{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
# f"🤖 {bot_name} in {chat_id}
# f"🔌 Service: {service}\n"
# f"🧠 Model: {model}\n"
# f"🌡️ Temperature: {temperature}\n"
# f"🔢 Max Tokens: {token}\n"
# f'ℹ️ Send "/help" for help'

import logging
import os
from pathlib import Path
from typing import Any, Dict, List

import aiohttp

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    log_directory = "logs"
    os.makedirs(log_directory, exist_ok=True)

    log_filename = os.path.join(log_directory, "bot_log.log")

    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)


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
        self.session: aiohttp.ClientSession | None = None

        # download path
        self.download_path = Path(download_path) / bot_name / str(chat_id)
        self.download_path.mkdir(parents=True, exist_ok=True)

        # To Do: history path
        self.chat_history_path = Path(chat_history_path) / bot_name / str(chat_id)
        self.chat_history_path.mkdir(parents=True, exist_ok=True)

    async def init_session(self) -> None:
        self.session = aiohttp.ClientSession()

    async def close_session(self) -> None:
        if self.session:
            await self.session.close()

    async def send_message(self, text: str) -> Dict[str, Any]:
        payload = {"chat_id": self.chat_id, "text": text}
        try:
            # Error: Item "None" of "ClientSession | None" has no attribute "post"
            async with self.session.post(
                f"{self.api_url}/sendMessage", data=payload
            ) as response:
                result = await response.json()
                if response.status == 200:
                    logger.debug(f"Message sent to {self.chat_id}: {text}")
                    return result
                else:
                    error_msg = result.get("description", "Unknown error")
                    logger.error(f"Failed to send message: {error_msg}")
                    return {
                        "ok": False,
                        "error_code": response.status,
                        "description": error_msg,
                    }
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {"ok": False, "error_code": 500, "description": str(e)}

    async def get_updates(self, offset=None):
        try:
            params = {"offset": offset} if offset else {}
            async with self.session.get(
                f"{self.api_url}/getUpdates", params=params
            ) as response:
                result = await response.json()
                if response.status == 200:
                    logger.debug("Updates retrieved successfully.")
                    return result
                else:
                    logger.error(
                        f"Failed to get updates: {result.get('description', 'Unknown error')}"
                    )
                    return {
                        "ok": False,
                        "error_code": response.status,
                        "description": result.get("description", "Unknown error"),
                    }
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return {"ok": False, "error_code": 500, "description": str(e)}

    # Function to retrieve file details from Telegram API
    async def get_file(self, file_id: str) -> Dict[str, Any]:
        try:
            logger.info(f"[get_file] Requesting file details for file_id: {file_id}")

            # Request file details from Telegram API
            # Error: Item "None" of "ClientSession | None" has no attribute "post"
            async with self.session.post(
                f"{self.api_url}/getFile", data={"file_id": file_id}
            ) as response:
                result = await response.json()

                # Check if the response is successful
                if response.status == 200:
                    logger.debug(f"[get_file] File details retrieved: {result}")
                    return result
                else:
                    # Log error details
                    error_msg = result.get("description", "Unknown error")
                    logger.error(f"[get_file] Failed to get file details: {error_msg}")
                    await self.send_message(
                        f"Error: Could not retrieve file details.\nReason: {error_msg}"
                    )
                    return {
                        "ok": False,
                        "error_code": response.status,
                        "description": error_msg,
                    }

        except Exception as e:
            logger.error(f"[get_file] Error getting file details: {e}")
            await self.send_message(f"Exception: Failed to retrieve file info: {e}")
            return {"ok": False, "error_code": 500, "description": str(e)}

    # Function to download the file
    async def download_file(self, file_path: str) -> Dict[str, Any]:
        try:
            # Build download URL and destination path
            url = f"{self.download_base_url}/{file_path}"
            file_name = os.path.basename(file_path)
            destination = self.download_path / file_name

            logger.info(f"[download_file] Starting download from: {url}")
            logger.info(f"[download_file] Target download path: {destination}")

            # Print output for debugging
            print(f"📥 Starting download: {url}")
            print(f"📁 Target path: {destination}")

            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)
            logger.debug(f"[download_file] Directory ensured: {destination.parent}")

            # Check if the file extension is allowed
            # Error: "TelegramClient" has no attribute "is_allowed_extension"; maybe "allowed_extensions"?
            if not self.is_allowed_extension(file_name):
                msg = f"Rejected file: {file_name}. Unsupported file type."
                logger.warning(f"[download_file] {msg}")
                await self.send_message(f"⚠️ {msg}")
                return {
                    "ok": False,
                    "error_code": 400,
                    "description": "Unsupported file type",
                }

            # Perform file download
            # Item "None" of "ClientSession | None" has no attribute "get"
            async with self.session.get(url) as response:
                logger.debug(f"[download_file] Response status: {response.status}")
                logger.debug(f"[download_file] Response headers: {response.headers}")

                if response.status == 200:
                    content = await response.read()
                    logger.debug(
                        f"[download_file] File content length: {len(content)} bytes"
                    )

                    # Save the content to file
                    with open(destination, "wb") as f:
                        f.write(content)

                    # Verify that the file was saved successfully#
                    # I do not receive the following message in the chat anymore?
                    # the file is stored but no feedback at the moment
                    if destination.exists() and destination.stat().st_size > 0:
                        msg = f"✅ File downloaded successfully: {file_name}"
                        logger.info(f"[download_file] {msg}")
                        print(msg)
                        await self.send_message(msg)
                        return {"ok": True, "file_name": str(destination)}
                    else:
                        # If file is not correctly written
                        msg = f"❌ File write failed or empty: {destination}"
                        logger.error(f"[download_file] {msg}")
                        print(msg)
                        await self.send_message(f"❌ {msg}")
                        return {
                            "ok": False,
                            "error_code": 500,
                            "description": msg,
                        }
                else:
                    # Handle non-200 HTTP response
                    msg = f"❌ Failed to download file. HTTP {response.status}"
                    logger.error(f"[download_file] {msg}")
                    await self.send_message(f"❌ {msg}")
                    return {
                        "ok": False,
                        "error_code": response.status,
                        "description": msg,
                    }

        except Exception as e:
            # Catch any other errors during file download
            logger.exception(f"[download_file] Exception: {e}")
            await self.send_message(f"❌ Exception during download: {e}")
            return {"ok": False, "error_code": 500, "description": str(e)}


# Setup logging when module loads
setup_logging()
