from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..db.crud import get_or_create_user
from ..db.fsrs_crud import get_dict_words_for_user, get_custom_words_for_user
from ..utils.message_utils import send_long_message

router = Router()


@router.message(Command("my_words"))
async def my_words(message: Message):
    user, _ = await get_or_create_user(message.from_user.id)

    dict_rows = await get_dict_words_for_user(user.id)
    custom_rows = await get_custom_words_for_user(user.id)

    if not dict_rows and not custom_rows:
        await message.answer("📚 Вы ещё не начали учить слова!\n Напишите /learn или /custom_word")
        return

    lines = []

    if dict_rows:
        lines.append("📘 <b>Слова из словаря:</b>")
        for i, (_, word) in enumerate(dict_rows, 1):
            lines.append(f"{i}. {word.surface} ({word.reading}) — {word.meaning}")
        lines.append("")

    if custom_rows:
        lines.append("📝 <b>Ваши слова:</b>")
        for i, (_, word) in enumerate(custom_rows, 1):
            lines.append(f"{i}. {word.surface} ({word.reading}) — {word.meaning}")

    all_users_words = "\n".join(lines)
    await send_long_message(message, all_users_words)

    if custom_rows:
        await message.answer("💡 Чтобы удалить своё слово, отправьте /delete_custom_word")
