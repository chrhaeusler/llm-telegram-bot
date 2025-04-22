import logging
import os
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)


def setup_logging():
    log_directory = "logs"
    os.makedirs(log_directory, exist_ok=True)

    log_filename = os.path.join(log_directory, "bot_log.log")

    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Prevent adding multiple handlers in environments like Jupyter
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        # File handler
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.DEBUG)

        # Create a formatter and set it for the handlers
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # Add the handlers to the logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger


class TelegramClient:
    def __init__(self, token, chat_id, download_path="downloads"):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.download_base_url = f"https://api.telegram.org/file/bot{token}"
        self.session = None
        self.download_path = Path(download_path) / str(chat_id)
        self.download_path.mkdir(parents=True, exist_ok=True)

    async def init_session(self):
        """Initialize the aiohttp session."""
        self.session = aiohttp.ClientSession()

    async def close_session(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()

    async def send_message(self, text):
        """Send a message to the specified chat_id."""
        payload = {"chat_id": self.chat_id, "text": text}
        try:
            async with self.session.post(
                f"{self.api_url}/sendMessage", data=payload
            ) as response:
                result = await response.json()
                if response.status == 200:
                    logger.debug(f"Message sent to {self.chat_id}: {text}")
                    return result
                else:
                    logger.error(
                        f"Failed to send message: {result.get('description', 'Unknown error')}"
                    )
                    return {
                        "ok": False,
                        "error_code": response.status,
                        "description": result.get("description", "Unknown error"),
                    }
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {"ok": False, "error_code": 500, "description": str(e)}

    async def get_updates(self):
        """Retrieve the latest updates for the bot."""
        try:
            async with self.session.get(f"{self.api_url}/getUpdates") as response:
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

    async def get_file(self, file_id):
        """Retrieve file details using the file_id."""
        try:
            async with self.session.post(
                f"{self.api_url}/getFile", data={"file_id": file_id}
            ) as response:
                result = await response.json()
                if response.status == 200:
                    logger.debug(f"File details retrieved: {result}")
                    return result
                else:
                    logger.error(
                        f"Failed to get file details: {result.get('description', 'Unknown error')}"
                    )
                    return {
                        "ok": False,
                        "error_code": response.status,
                        "description": result.get("description", "Unknown error"),
                    }
        except Exception as e:
            logger.error(f"Error getting file details: {e}")
            return {"ok": False, "error_code": 500, "description": str(e)}

    async def download_file(self, file_path):
        """Download a file using its file_path."""
        try:
            url = f"{self.download_base_url}/{file_path}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    file_name = os.path.basename(file_path)
                    destination = self.download_path / file_name
                    with open(destination, "wb") as file:
                        file.write(content)
                    logger.info(f"File downloaded: {destination}")
                    return {"ok": True, "file_name": str(destination)}
                else:
                    logger.error(f"Failed to download file: HTTP {response.status}")
                    return {
                        "ok": False,
                        "error_code": response.status,
                        "description": "Failed to download",
                    }
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return {"ok": False, "error_code": 500, "description": str(e)}


# Initialize logging when module is loaded
setup_logging()
