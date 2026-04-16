from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timezone

from ..db.base import AsyncSessionLocal
from ..db.fsrs_models import FSRSCard, CustomWord
from ..db.crud import get_or_create_user

router = Router()


class AddWordStates(StatesGroup):
    waiting_for_data = State()


@router.message(Command("custom_word"))
async def cmd_add(message: Message, state: FSMContext):

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_custom_word")]
    ])

    sent_msg = await message.answer(
        "📝 Отправьте данные в формате (каждое поле с новой строки):\n\n"
        "<b>Слово</b>\n"
        "<b>Чтение</b> (или -)\n"
        "<b>Перевод</b>\n\n"
        "Пример:\n"
        "食べる\n"
        "たべる\n"
        "есть",
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

    if len(lines) != 3:
        await message.answer(
            "⚠️ Неправильный формат. Нужно ровно 3 строки:\n"
            "1. Слово\n2. Чтение (или -)\n3. Перевод\n\n"
            "Попробуйте отправить ещё раз:"
        )
        return

    surface, reading, meaning = lines
    user, _ = await get_or_create_user(message.from_user.id)

    async with AsyncSessionLocal() as session:
        custom_word = CustomWord(
            user_id=user.id,
            surface=surface,
            reading=reading,
            meaning=meaning
        )
        session.add(custom_word)
        await session.flush()

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        fsrs_card = FSRSCard(
            user_id=user.id,
            word_id=custom_word.id,
            word_type="custom",
            due=now,
            stability=0.1,
            difficulty=5.0,
            reps=0,
            lapses=0
        )
        session.add(fsrs_card)
        await session.commit()

    fsm_data = await state.get_data()
    instruction_msg_id = fsm_data.get("instruction_msg_id")
    try:
        if instruction_msg_id:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=instruction_msg_id)
    except Exception:
        pass

    await state.clear()
    await message.answer(f"✅ Слово <b>{surface}</b> успешно добавлено в колоду!", parse_mode="HTML")
