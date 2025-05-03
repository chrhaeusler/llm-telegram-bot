# run with "PYTHONPATH=. python3 tests/test_telegram_client.py"
import asyncio

from llm_telegram_bot.config.config_loader import load_config
from llm_telegram_bot.telegram.client import TelegramClient


async def main():
    config = load_config()
    download_path = config["telegram"]["download_path"]
    bot_config = config["telegram"]["bot_1"]
    bot_name = bot_config["name"]
    token = bot_config["token"]
    chat_id = bot_config["chat_id"]
    chat_history_path = config["telegram"]["chat_history_path"]  # Add this line

    client = TelegramClient(
        token=token,
        chat_id=chat_id,
        bot_name=bot_name,
        download_path=download_path,
        chat_history_path=chat_history_path,  # And pass it in
    )
    await client.init_session()

    # 1. Send test message
    print("Sending test message...")
    await client.send_message("🤖 Test message from client.py!")

    # 2. Poll updates to find a file (if user sends one)
    print("Waiting for file... please upload a file to the bot chat!")

    try:
        updates = await client.get_updates()

        if updates["ok"] and updates["result"]:
            for update in updates["result"]:
                message = update.get("message", {})
                document = message.get("document")
                audio = message.get("audio")
                video = message.get("video")
                photo = message.get("photo")

                file_id = None
                if document:
                    file_id = document["file_id"]
                elif audio:
                    file_id = audio["file_id"]
                elif video:
                    file_id = video["file_id"]
                elif photo:
                    file_id = photo[-1]["file_id"]  # highest resolution photo

                if file_id:
                    file_info = await client.get_file(file_id)
                    if file_info["ok"]:
                        file_path = file_info["result"]["file_path"]
                        await client.download_file(file_path)

            # ✅ Acknowledge all updates so they aren't fetched again
            last_update_id = updates["result"][-1]["update_id"]
            await client.get_updates(offset=last_update_id + 1)

        else:
            print("No new updates.")

    finally:
        await client.close_session()


if __name__ == "__main__":
    asyncio.run(main())
