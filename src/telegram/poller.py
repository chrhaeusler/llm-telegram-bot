# test with "python -m src.telegram.poller bot_1"

import asyncio
import datetime
import logging
import os
import time
from typing import Any

import aiohttp

from src.config_loader import load_config
from src.telegram.client import TelegramClient

# Create logger
logger = logging.getLogger(__name__)


class PollingLoop:
    def __init__(self, bot_name: str, client: TelegramClient, config: dict[str, Any]):
        self.bot_name = bot_name
        # assuming client has methods like get_updates, get_file, send_message
        self.client = client
        self.config = config
        self.bot_config = config["telegram"].get(bot_name, {})

        self.active_interval = self.bot_config.get(
            "polling_interval_active",
            config["telegram"].get("polling_interval_active", 5),
        )
        self.idle_interval = self.bot_config.get(
            "polling_interval_idle",
            config["telegram"].get("polling_interval_idle", 60),
        )

        self.last_event_time = time.time()
        self.current_interval = self.active_interval
        self.last_update_id = None

        # Update download path to include bot_name and chat_id
        self.download_dir = os.path.join(
            config["telegram"].get("download_path", "./tmp"),
            self.bot_name,
            str(
                self.client.chat_id
            ),  # Ensure chat_id is a string for proper path joining
        )
        os.makedirs(
            self.download_dir, exist_ok=True
        )  # Create the directory if it doesn't exist

        self._running = True

    def stop(self):
        self._running = False

    async def run(self):
        logging.info(f"[PollingLoop] Started polling for bot '{self.bot_name}'")
        while self._running:
            try:
                updates = await self.client.get_updates(offset=self.last_update_id)

                if updates["ok"] and updates["result"]:
                    for update in updates["result"]:
                        self.last_update_id = update["update_id"] + 1
                        await self.handle_update(update)

                    # Got updates, reset idle counter and polling interval
                    self.last_event_time = time.time()
                    if self.current_interval != self.active_interval:
                        logging.info(
                            f"[PollingLoop] Activity detected. Switching to active interval: {self.active_interval}s"
                        )
                    self.current_interval = self.active_interval

                else:
                    idle_time = time.time() - self.last_event_time
                    if idle_time > 300:
                        new_interval = min(
                            self.current_interval + self.active_interval,
                            self.idle_interval,
                        )
                        if new_interval != self.current_interval:
                            last_seen = datetime.datetime.fromtimestamp(
                                self.last_event_time
                            ).strftime("%Y-%m-%d %H:%M:%S")
                            logging.info(
                                f"[PollingLoop] No activity for {int(idle_time)}s (last event: {last_seen}). "
                                f"Adjusting polling interval to {new_interval}s"
                            )
                        self.current_interval = new_interval

                await asyncio.sleep(self.current_interval)

            except asyncio.CancelledError:
                logging.info("[PollingLoop] Cancelled by shutdown signal.")
                break
            except Exception as e:
                logging.exception(f"[PollingLoop] Error during polling: {e}")
                await asyncio.sleep(self.idle_interval)

    async def handle_update(self, update: dict[str, Any]):
        try:
            logging.info(f"[PollingLoop] Received update: {update}")

            # Check if the update contains a message and a document
            if "message" in update and "document" in update["message"]:
                message = update["message"]
                file_id = message["document"]["file_id"]
                file_name = message["document"]["file_name"]
                logging.info(f"Document received: {file_name} (file_id: {file_id})")

                # Set chat_id to the correct chat_id in TelegramClient
                self.client.chat_id = message["chat"]["id"]  # Set chat_id here

                # Get the file details using the file_id
                file_details = await self.get_file(file_id)
                if file_details["ok"]:
                    file_path = file_details["result"]["file_path"]
                    await self.download_file(file_path, file_name)
                else:
                    logging.error(f"Failed to get file details for file_id: {file_id}")
                    await self.send_message(
                        f"❌ Error retrieving file details for {file_name}"
                    )

        except Exception as e:
            logging.error(f"Error processing update: {e}")
            chat_id = update.get("message", {}).get("chat", {}).get("id", None)
            if chat_id:
                await self.send_message(f"❌ Error processing your request: {e}")
            else:
                logging.error(
                    "Error: No valid chat_id found to send the error message."
                )

    # Assuming 'get_file' is part of the Telegram client
    async def get_file(self, file_id: str):
        """Fetches file details using the Telegram client"""
        try:
            file_details = await self.client.get_file(file_id)
            return file_details
        except Exception as e:
            logging.error(f"Error fetching file details: {e}")
            return {"ok": False}

    async def download_file(self, file_path: str, file_name: str):
        """Download the file using its file_path and save it with the original file name"""
        try:
            download_url = (
                f"https://api.telegram.org/file/bot{self.client.token}/{file_path}"
            )
            # Ensure you have a directory for downloads with chat_id subfolder
            os.makedirs(self.download_dir, exist_ok=True)

            file_path_on_disk = os.path.join(self.download_dir, file_name)
            logging.info(f"Downloading file to {file_path_on_disk}")

            # Fetch the file content
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status == 200:
                        with open(file_path_on_disk, "wb") as f:
                            f.write(await response.read())
                        logging.info(f"File downloaded successfully: {file_name}")
                    else:
                        logging.error(f"Failed to download file: {response.status}")
                        await self.send_message(
                            f"❌ Error downloading file {file_name}"
                        )
        except Exception as e:
            logging.error(f"Error downloading file {file_name}: {e}")
            await self.send_message(f"❌ Error downloading file {file_name}")

    async def send_message(self, text: str):
        """Sends a message back to the user"""
        try:
            # Ensure self.client.chat_id is set
            if not self.client.chat_id:
                logging.error("Error: chat_id not available.")
                return

            # Send the message with the chat_id
            result = await self.client.send_message(text=text)
            if result["ok"]:
                logging.info(f"Message sent to {self.client.chat_id}: {text}")
            else:
                logging.error(
                    f"Failed to send message: {result.get('description', 'Unknown error')}"
                )
        except Exception as e:
            logging.error(f"Error sending message: {e}")


if __name__ == "__main__":
    import sys

    async def main():
        config = load_config()
        bot_names = sys.argv[1:] or list(config["telegram"].keys())
        # bot_names = [bot_name for bot_name in bot_names if bot_name.startswith("bot_")]
        bot_names = [
            bot_name
            for bot_name in bot_names
            if bot_name.startswith("bot_")
            and config["telegram"].get(bot_name, {}).get("enabled", False)
        ]

        tasks = []
        for bot_name in bot_names:
            # Debugging log to check bot_config and bot_name
            print(f"Bot Name: {bot_name}")
            bot_config = config["telegram"].get(bot_name, {})
            print(f"Bot Config: {bot_config}")

            if not isinstance(bot_config, dict):
                raise ValueError(
                    f"Bot configuration for {bot_name} is not a dictionary: {bot_config}"
                )
            bot_config = config["telegram"][bot_name]
            client = TelegramClient(
                token=bot_config["token"],
                chat_id=bot_config["chat_id"],
                bot_name=bot_name,
                download_path=config["telegram"]["download_path"],
                chat_history_path=config["telegram"]["chat_history_path"],
            )
            await client.init_session()

            poller = PollingLoop(bot_name, client, config)
            task = asyncio.create_task(poller.run())
            tasks.append(task)

        logging.info(f"[Main] Started {len(tasks)} bot(s): {', '.join(bot_names)}")
        await asyncio.gather(*tasks)

    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
