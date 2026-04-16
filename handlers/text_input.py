from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from wanakana.utils import is_char_japanese

from ..db.crud import get_or_create_user
from ..db.crud import AsyncSessionLocal

from ..services.text_analysis import JLPTAnalyzer
from ..services.grammar_analysis import analyze_grammar_jlpt

import asyncio

router = Router()


@router.message(Command("analyze"))
async def cmd_analyze(message: Message):
    await message.answer(
        "Отправь мне японский текст, и я оценю его уровень JLPT."
    )


@router.message()
async def handle_user_text(message: Message):
    user, _ = await get_or_create_user(message.from_user.id)
    text_content = message.text

    if not any(is_char_japanese(char) for char in text_content):
        await message.answer(
            "Я анализирую тексты на японском языке\n"
            "Отправь текст или начни учить слова командой /learn 🤓\n"
        )
        return

    # Лексика
    async with AsyncSessionLocal() as session:
        analyzer = JLPTAnalyzer(session)
        jlpt_result = await analyzer.analyze_text_jlpt(text_content)

    # Грамматика
    # grammar_level = "В разработке"
    grammar_level = await analyze_grammar_jlpt(text_content)

    await message.answer(
        f"📊 Результат анализа:\n\n"
        f"📘 Лексика:\n{jlpt_result}\n\n"
        f"📗 Грамматика:\n{grammar_level}"
    )
