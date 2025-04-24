from src.commands.commands_registry import register_command


@register_command("/undo")
async def saveresponse_handler(session, message, args):
    await session.send_message("⚠️ /sr not yet implemented.")
