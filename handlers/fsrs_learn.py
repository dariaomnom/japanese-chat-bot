from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime, timezone

from ..db.fsrs_crud import get_or_create_fsrs_card, get_due_fsrs_cards, update_fsrs_card, add_new_fsrs_words
from ..db.crud import get_or_create_user
from ..services.fsrs import fsrs_engine, RATING_MAP
from ..db.models import DictionaryWord
from ..db.fsrs_models import CustomWord
from sqlalchemy import select
from ..db.base import AsyncSessionLocal

router = Router()
FSRS_PREFIX = "fsrs_"


def get_fsrs_keyboard(word_id: int, word_type: str, show_only_meaning_btn: bool = True) -> InlineKeyboardMarkup:
    """
    Генерирует клавиатуру в зависимости от этапа:
    - show_only_meaning_btn=True: только кнопка "Показать перевод"
    - show_only_meaning_btn=False: только 4 кнопки оценки
    """
    type_prefix = f"{FSRS_PREFIX}{word_type}_"
    if show_only_meaning_btn:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👀 Показать перевод", callback_data=f"{type_prefix}meaning_{word_id}")]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="😨 Again", callback_data=f"{type_prefix}again_{word_id}"),
                InlineKeyboardButton(text="🤔 Hard", callback_data=f"{type_prefix}hard_{word_id}"),
                InlineKeyboardButton(text="🙂 Good", callback_data=f"{type_prefix}good_{word_id}"),
                InlineKeyboardButton(text="😎 Easy", callback_data=f"{type_prefix}easy_{word_id}"),
            ]
        ])


@router.message(Command("learn"))
async def start_fsrs_learning(message: Message):
    try:
        user, _ = await get_or_create_user(message.from_user.id)
        due_cards = await get_due_fsrs_cards(user.id, limit=1)

        limit = user.words_per_day if user.words_per_day is not None else 5
        if limit > 0 and not due_cards:
            new_words = await add_new_fsrs_words(user.id, count=limit)
            if new_words:
                due_cards = await get_due_fsrs_cards(user.id, limit=1)

        if due_cards:
            card_data = due_cards[0]
            keyboard = get_fsrs_keyboard(card_data.word_id, card_data.word_type, show_only_meaning_btn=True)
            await message.answer(f"<b>{card_data.surface}</b>", reply_markup=keyboard, parse_mode="HTML")
        else:
            await message.answer("🎉 Все слова на сегодня изучены!")

    except Exception as e:
        print(f"Ошибка в /learn: {e}")
        import traceback
        traceback.print_exc()
        await message.answer("Произошла ошибка, попробуйте позже :(")


@router.callback_query(lambda c: c.data.startswith(FSRS_PREFIX))
async def handle_fsrs_callback(callback: CallbackQuery):
    data = callback.data
    parts = data.split("_")
    if len(parts) != 4:
        await callback.answer("Ошибка данных", show_alert=True)
        return

    word_type = parts[1]
    action = parts[2]
    word_id = int(parts[3])

    user, _ = await get_or_create_user(callback.from_user.id)

    async with AsyncSessionLocal() as session:
        if word_type == "dict":
            stmt = select(DictionaryWord).where(DictionaryWord.id == word_id)
        elif word_type == "custom":
            stmt = select(CustomWord).where(CustomWord.id == word_id)
        else:
            await callback.answer("Неизвестный тип слова", show_alert=True)
            return

        word = (await session.execute(stmt)).scalar_one_or_none()

    if not word:
        await callback.answer("Слово не найдено", show_alert=True)
        return

    if action == "meaning":
        new_markup = get_fsrs_keyboard(word_id, word_type, show_only_meaning_btn=False)
        try:
            await callback.message.edit_text(
                f"<b>{word.surface}</b> ({word.reading})\n\n{word.meaning}",
                reply_markup=new_markup,
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            pass
        await callback.answer()
        return

    if action in RATING_MAP:
        rating = RATING_MAP[action]
        now = datetime.now(timezone.utc)

        db_card = await get_or_create_fsrs_card(user.id, word_id)
        fsrs_card_obj = fsrs_engine.dict_to_card(db_card.stability, db_card.difficulty, db_card.last_review,
                                                 db_card.due)
        new_card = fsrs_engine.repeat(fsrs_card_obj, now, rating)

        is_lapse = (action == "again")
        await update_fsrs_card(db_card, fsrs_engine.card_to_dict(new_card), is_lapse)

        if db_card.reps == 1:
            await callback.message.answer(
                f"<b>{word.surface}</b> ({word.reading})\n{word.meaning}",
                parse_mode="HTML"
            )

        await callback.message.delete()

        due_cards = await get_due_fsrs_cards(user.id, limit=1)
        if due_cards:
            next_item = due_cards[0]
            keyboard = get_fsrs_keyboard(next_item.word_id, next_item.word_type, show_only_meaning_btn=True)
            await callback.message.answer(f"<b>{next_item.surface}</b>", reply_markup=keyboard, parse_mode="HTML")
        else:
            await callback.message.answer("🏁 Карточки на сегодня закончились!")

    await callback.answer()
