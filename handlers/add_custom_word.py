from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from ..db.crud import get_or_create_user
from ..db.fsrs_crud import add_custom_words

router = Router()


class AddWordStates(StatesGroup):
    waiting_for_data = State()


@router.message(Command("custom_word"))
async def cmd_add(message: Message, state: FSMContext):

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_custom_word")]
    ])

    sent_msg = await message.answer(
        "📝 Отправьте одно или несколько слов в формате:\n\n"
        "<b>Слово</b>\n"
        "<b>Чтение</b> (или -)\n"
        "<b>Перевод</b>\n\n"
        "Пример:\n"
        "食べる\n"
        "たべる\n"
        "есть\n",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.update_data(instruction_msg_id=sent_msg.message_id)
    await state.set_state(AddWordStates.waiting_for_data)


@router.callback_query(F.data == "cancel_custom_word")
async def cancel_add(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("Добавление слова отменено")
    await callback.answer()


@router.message(AddWordStates.waiting_for_data, F.text)
async def process_add_word(message: Message, state: FSMContext):
    lines = [line.strip() for line in message.text.splitlines() if line.strip()]

    if not lines or len(lines) % 3 != 0:
        await message.answer(
            "⚠️ Неправильный формат. Данные должны идти блоками по 3 строки:\n"
            "Слово\nЧтение (или -)\nПеревод\n\n"
            "Если слов несколько, просто отправьте их друг за другом."
        )
        return

    words_data = []
    for i in range(0, len(lines), 3):
        words_data.append((lines[i], lines[i + 1], lines[i + 2]))

    user, _ = await get_or_create_user(message.from_user.id)

    added_count, errors = await add_custom_words(user.id, words_data)

    fsm_data = await state.get_data()
    instruction_msg_id = fsm_data.get("instruction_msg_id")
    try:
        if instruction_msg_id:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=instruction_msg_id)
    except Exception:
        pass

    await state.clear()

    if added_count > 0:
        last_surface = words_data[-1][0] if words_data else ""
        if added_count == 1:
            result_msg = f"✅ Слово <b>{last_surface}</b> успешно добавлено в колоду!"
        else:
            result_msg = f"✅ Успешно добавлено слов: <b>{added_count}</b>"
        if errors:
            result_msg += f"\n\n⚠️ Ошибки при добавлении:\n" + "\n".join(errors[:])
        await message.answer(result_msg, parse_mode="HTML")
    else:
        await message.answer("Не удалось добавить ни одного слова. Проверьте формат.")
