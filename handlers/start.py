from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..db.crud import get_or_create_user

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):

    user, _ = await get_or_create_user(message.from_user.id)

    await message.answer(
        "Привет! こんにちは！ 🇯🇵\n"
        "Это бот поможет тебе выучить японские слова и узнать уровень текста по JLPT 🤓\n"
        "/analyze - узнать сложность текста\n"
        "/learn - начать учить слова\n"
        "/my_words - список изучаемых слов\n"
        "/custom_word - добавить свое слово\n"
        "/settings - настройки\n"
    )
