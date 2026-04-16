from sqlalchemy import select, delete
from datetime import datetime, timezone
from typing import List, Tuple
from dataclasses import dataclass

from .base import AsyncSessionLocal
from .fsrs_models import FSRSCard
from .models import User, DictionaryWord
from .fsrs_models import CustomWord

@dataclass
class UnifiedWordCard:
    word_id: int
    word_type: str  # dict / custom
    surface: str
    reading: str
    meaning: str
    fsrs_card: FSRSCard


async def get_due_fsrs_cards(user_id: int, limit: int = 20) -> List[UnifiedWordCard]:
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cards = []

        # Словарные слова
        dict_stmt = select(FSRSCard, DictionaryWord).join(
            DictionaryWord, FSRSCard.word_id == DictionaryWord.id
        ).where(
            FSRSCard.user_id == user_id,
            FSRSCard.word_type == "dict",
            FSRSCard.due <= now
        ).order_by(FSRSCard.due.asc())

        for card, dw in (await session.execute(dict_stmt)).all():
            cards.append(UnifiedWordCard(
                word_id=dw.id, word_type="dict",
                surface=dw.surface, reading=dw.reading or "",
                meaning=dw.meaning,
                fsrs_card=card
            ))

        # Пользовательские слова
        custom_stmt = select(FSRSCard, CustomWord).join(
            CustomWord, FSRSCard.word_id == CustomWord.id
        ).where(
            FSRSCard.user_id == user_id,
            FSRSCard.word_type == "custom",
            FSRSCard.due <= now
        ).order_by(FSRSCard.due.asc())

        for card, cw in (await session.execute(custom_stmt)).all():
            cards.append(UnifiedWordCard(
                word_id=cw.id, word_type="custom",
                surface=cw.surface, reading=cw.reading or "",
                meaning=cw.meaning or "",
                fsrs_card=card
            ))

        # Объединение и сортировка
        cards.sort(key=lambda x: x.fsrs_card.due)
        return cards[:limit]


async def get_or_create_fsrs_card(user_id: int, word_id: int) -> FSRSCard:
    """Возвращает карточку или создаёт новую"""
    async with AsyncSessionLocal() as session:
        stmt = select(FSRSCard).where(
            FSRSCard.user_id == user_id,
            FSRSCard.word_id == word_id
        )
        result = await session.execute(stmt)
        card = result.scalar_one_or_none()

        if card:
            return card

        card = FSRSCard(
            user_id=user_id,
            word_id=word_id,
            due=datetime.now(timezone.utc),
            stability=0.1,
            difficulty=5.0
        )
        session.add(card)
        await session.commit()
        await session.refresh(card)
        return card


async def update_fsrs_card(card: FSRSCard, state: dict, is_lapse: bool = False):
    """Обновляет состояние карточки после ответа"""
    async with AsyncSessionLocal() as session:
        card.stability = state["stability"]
        card.difficulty = state["difficulty"]
        card.last_review = state.get("last_review")
        card.due = state["due"]
        card.reps += 1
        if is_lapse:
            card.lapses += 1

        session.add(card)
        await session.commit()
        await session.refresh(card)


async def add_new_fsrs_words(user_id: int, count: int = 5) -> list:
    """
    Добавляет новые слова постепенно от легких (N5) к сложным.
    Внутри текущего уровня слова выбираются случайно.
    """
    async with AsyncSessionLocal() as session:
        # Проверка, учил ли пользователь новые слова сегодня
        user = await session.get(User, user_id)
        if user.last_new_words_date and user.last_new_words_date.date() == datetime.now(timezone.utc).date():
            return []

        # ID слов, которые уже добавлены пользователю
        existing_ids_stmt = select(FSRSCard.word_id).where(FSRSCard.user_id == user_id)
        existing_ids_result = await session.execute(existing_ids_stmt)
        existing_ids = {row[0] for row in existing_ids_result.fetchall()}

        jlpt_levels = ["N5", "N4", "N3", "N2", "N1"]
        selected_words = []

        for level in jlpt_levels:
            stmt = select(DictionaryWord).where(DictionaryWord.jlpt_level == level)

            if existing_ids:
                stmt = stmt.where(~DictionaryWord.id.in_(existing_ids))

            result = await session.execute(stmt)
            available_in_level = result.scalars().all()

            if available_in_level:
                import random
                needed = count - len(selected_words)
                take = min(needed, len(available_in_level))
                selected_words.extend(random.sample(available_in_level, take))
                break

        if not selected_words:
            return []

        # Создание карточек FSRS
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        fsrs_cards = [
            FSRSCard(
                user_id=user_id,
                word_id=w.id,
                stability=0.1,
                difficulty=5.0,
                due=now_naive,
                last_review=None,
                reps=0,
                lapses=0
            )
            for w in selected_words
        ]

        session.add_all(fsrs_cards)

        # Обновление даты последнего добавления
        user = await session.get(User, user_id)
        user.last_new_words_date = now_naive

        await session.commit()
        return selected_words


async def get_dict_words_for_user(user_id: int):
    async with AsyncSessionLocal() as session:
        stmt = (
            select(FSRSCard, DictionaryWord)
            .join(DictionaryWord, FSRSCard.word_id == DictionaryWord.id)
            .where(FSRSCard.user_id == user_id)
            .where(FSRSCard.word_type == "dict")
            .order_by(FSRSCard.due.asc())
        )
        return (await session.execute(stmt)).all()


async def get_custom_words_for_user(user_id: int):
    async with AsyncSessionLocal() as session:
        stmt = (
            select(FSRSCard, CustomWord)
            .join(CustomWord, FSRSCard.word_id == CustomWord.id)
            .where(FSRSCard.user_id == user_id)
            .where(FSRSCard.word_type == "custom")
            .order_by(FSRSCard.due.asc())
        )
        return (await session.execute(stmt)).all()


async def delete_custom_word(user_id: int, custom_word_id: int) -> bool:
    """Удаляет кастомное слово и связанную с ним FSRS-карточку"""
    async with AsyncSessionLocal() as session:
        stmt = select(CustomWord).where(
            CustomWord.id == custom_word_id,
            CustomWord.user_id == user_id
        )
        word = (await session.execute(stmt)).scalar_one_or_none()
        if not word:
            return False

        await session.execute(
            delete(FSRSCard).where(
                FSRSCard.word_id == custom_word_id,
                FSRSCard.word_type == "custom",
                FSRSCard.user_id == user_id
            )
        )

        await session.delete(word)
        await session.commit()
        return True