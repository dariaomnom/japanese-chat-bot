from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, BotCommand
import asyncio
import sys
from pathlib import Path
from .config import BOT_TOKEN

from .db.base import init_db
from .handlers.start import router as start_router
from .services.load_dictionary import load_dictionary
from .handlers.text_input import router as text_router
from .handlers.my_words import router as words_router
from .handlers.fsrs_learn import router as fsrs_router
from .handlers.settings import router as settings_router
from .handlers.add_custom_word import router as add_custom_router
from .handlers.delete_custom_word import router as delete_custom_router

sys.path.append(str(Path(__file__).parent.parent.resolve()))


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Начать"),
        BotCommand(command="analyze", description="Анализ текста"),
        BotCommand(command="learn", description="Изучение слов"),
        BotCommand(command="my_words", description="Слова, которые изучаю"),
        BotCommand(command="custom_word", description="Добавить свое слово"),
        BotCommand(command="settings", description="Настройки"),
    ]
    await bot.set_my_commands(commands)


async def main():
    await init_db()

    await load_dictionary()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(fsrs_router)
    dp.include_router(words_router)
    dp.include_router(settings_router)
    dp.include_router(add_custom_router)
    dp.include_router(delete_custom_router)
    dp.include_router(text_router)

    await set_commands(bot)

    print("Бот запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())