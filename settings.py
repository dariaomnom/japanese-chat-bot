from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from ..db.crud import get_or_create_user, set_user_words_limit

router = Router()

OPTIONS = [0, 5, 10, 15, 20, 25]


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    user, _ = await get_or_create_user(message.from_user.id)
    current_limit = user.words_per_day if user.words_per_day is not None else 5

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"{'✅ ' if current_limit == val else ''}{val}",
                callback_data=f"set_limit_{val}"
            )
            for val in row
        ]
        for row in [OPTIONS[i:i + 3] for i in range(0, len(OPTIONS), 3)]
    ])

    await message.answer(
        f"⚙️ <b>Настройки обучения</b>\n\n"
        f"Текущий лимит: <b>{current_limit} новых слов в день</b>\n"
        f"Выберите новое значение:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("set_limit_"))
async def process_set_limit(callback: CallbackQuery):
    try:
        new_limit = int(callback.data.split("_")[-1])
        await set_user_words_limit(callback.from_user.id, new_limit)
        await callback.message.delete()
        await callback.message.answer(f"✅ Установлено {new_limit} слов в день")
        await callback.answer()
    except ValueError:
        await callback.answer("Ошибка данных", show_alert=True)

