import asyncio
from pathlib import Path

from src.config_loader import load_combined_config
from src.telegram.client import TelegramClient

CONFIG_PATH = Path("config/config.yaml")


async def test_client_and_file():
    # Read from config
    config = load_combined_config()
    bot_config = config["telegram"]["bot_1"]
    token = bot_config["token"]
    chat_id = bot_config["chat_id"]

    # Initialize Telegram client
    bot = TelegramClient(token=token, chat_id=chat_id)
    await bot.init_session()

    # Test send message
    response = await bot.send_message("Hello, this is a test!")
    print("Send message response:", response)

    # Test get updates
    updates = await bot.get_updates()
    print("Updates:", updates)

    # File handling (optional, will only attempt if a document is found)
    if updates.get("ok") and "result" in updates:
        for message in updates["result"]:
            if "document" in message:
                file_id = message["document"]["file_id"]
                print(f"Found file ID: {file_id}")

                file_details = await bot.get_file(file_id)
                print("File details:", file_details)

                if file_details.get("ok"):
                    file_path = file_details["result"]["file_path"]
                    print(f"File path: {file_path}")
                    await bot.download_file(file_path)

    await bot.close_session()


if __name__ == "__main__":
    asyncio.run(test_client_and_file())
