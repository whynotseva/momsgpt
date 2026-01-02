import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from app.bot.handlers import start, admin

async def main():
    logging.basicConfig(level=logging.INFO)
    
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("Error: BOT_TOKEN is not set")
        return

    bot = Bot(token=bot_token)
    dp = Dispatcher()
    
    dp.include_router(start.router)
    dp.include_router(admin.router)

    # Setup Menu Commands
    from aiogram.types import BotCommand
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="profile", description="👤 Личный кабинет"),
        BotCommand(command="buy", description="💳 Купить VPN"),
        BotCommand(command="help", description="🆘 Помощь")
    ]
    await bot.set_my_commands(commands)
    
    print("🤖 Bot is starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
