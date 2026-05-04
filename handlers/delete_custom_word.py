from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from ..utils.message_utils import send_long_message
from ..db.crud import get_or_create_user
from ..db.fsrs_crud import get_custom_words_for_user, delete_custom_word

router = Router()


class DeleteWordStates(StatesGroup):
    waiting_for_number = State()


@router.message(Command("delete_custom_word"))
async def cmd_delete_word(message: Message, state: FSMContext):
    user, _ = await get_or_create_user(message.from_user.id)
    custom_rows = await get_custom_words_for_user(user.id)

    if not custom_rows:
        await message.answer("📭 У вас нет кастомных слов для удаления.")
        return

    lines = ["🗑 <b>Выберите номер слова для удаления:</b>\n"]
    for i, (_, word) in enumerate(custom_rows, 1):
        lines.append(f"{i}. {word.surface} ({word.reading}) — {word.meaning}")

    lines.append("\n🔢 Отправьте номер слова (например: 2)")

    instruction_text = "\n".join(lines)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_delete_custom")]
    ])

    msg_ids = await send_long_message(message, instruction_text)
    if msg_ids:
        last_msg_id = msg_ids[-1]
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=last_msg_id,
                reply_markup=keyboard
            )
        except Exception:
            pass

    await state.update_data(
        custom_rows=custom_rows,
        instruction_msg_ids=msg_ids
    )
    await state.set_state(DeleteWordStates.waiting_for_number)


@router.callback_query(F.data == "cancel_delete_custom")
async def cancel_delete(callback: CallbackQuery, state: FSMContext):
    fsm_data = await state.get_data()
    msg_ids = fsm_data.get("instruction_msg_ids", [])

    for msg_id in msg_ids:
        try:
            await callback.message.bot.delete_message(chat_id=callback.message.chat.id, message_id=msg_id)
        except Exception:
            pass

    await state.clear()
    await callback.message.answer("Удаление отменено.")
    await callback.answer()


@router.message(DeleteWordStates.waiting_for_number, F.text)
async def process_delete_word(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("⚠️ Пожалуйста, отправьте только число (номер из списка).")
        return

    num = int(text)
    fsm_data = await state.get_data()
    custom_rows = fsm_data.get("custom_rows", [])
    msg_ids = fsm_data.get("instruction_msg_ids", [])

    if num < 1 or num > len(custom_rows):
        await message.answer(f"⚠️ Номер должен быть от 1 до {len(custom_rows)}.")
        return

    _, target_word = custom_rows[num - 1]
    word_id = target_word.id
    user, _ = await get_or_create_user(message.from_user.id)

    success = await delete_custom_word(user.id, word_id)

    for msg_id in msg_ids:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
        except Exception:
            pass

    await state.clear()

    if success:
        await message.answer(f"✅ Слово <b>{target_word.surface}</b> удалено из колоды.", parse_mode="HTML")
    else:
        await message.answer("Не удалось удалить слово.")
