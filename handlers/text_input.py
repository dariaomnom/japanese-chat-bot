import asyncio
import os
import re
import time
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from wanakana.utils import is_char_japanese

from ..db.crud import get_or_create_user, AsyncSessionLocal
from ..services.lexical_analysis import JLPTAnalyzer
from ..services.grammar_analysis import analyze_grammar_jlpt
from ..utils.message_utils import send_long_message

router = Router()

LOG_DIR = "../data"
LOG_FILE = os.path.join(LOG_DIR, "analysis_time.log")


def ensure_log_dir():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)


def log_execution_time(text_preview: str, text_length: int, lex_time: float, gram_time: float, total_time: float, grammar_level: str):
    """Записывает замер времени в лог-файл"""
    ensure_log_dir()

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    preview = text_preview[:25].replace("\n", " ") + "..." if len(text_preview) > 50 else text_preview

    log_entry = (
        f"[{date_str} {time_str}] "
        f"Len: {text_length:>4} chars | "
        f"Total: {total_time:.4f}s | "
        f"Lex: {lex_time:.4f}s | "
        f"Gram: {gram_time:.4f}s | "
        f"Level: {grammar_level} | "
        f"Text: \"{preview}\"\n"
    )

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)


def clean_text_for_analysis(text: str) -> str:
    return re.sub(r'\s+', '', text)


@router.message(Command("analyze"))
async def cmd_analyze(message: Message):
    full_text = message.text
    parts = full_text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "📝 Отправь мне японский текст, и я оценю его уровень JLPT"
        )
        return
    await process_analysis(message, parts[1].strip())


@router.message(F.text)
async def handle_user_text(message: Message):
    text_content = message.text
    await process_analysis(message, text_content)


async def process_analysis(message: Message, text_content: str):
    """Общая логика анализа текста"""
    if not any(is_char_japanese(char) for char in text_content):
        await message.answer(
            "🇯🇵 Я анализирую тексты только на японском языке.\n"
            "Отправь текст или начни учить слова командой /learn 🤓"
        )
        return

    user, _ = await get_or_create_user(message.from_user.id)
    loading_msg = await message.answer("⏳ Анализирую лексику и грамматику...")

    start_total = time.time()
    lex_time = 0.0
    gram_time = 0.0

    text_content = clean_text_for_analysis(text_content)

    try:
        # Лексика
        start_lex = time.time()
        async with AsyncSessionLocal() as session:
            analyzer = JLPTAnalyzer(session)
            jlpt_result = await analyzer.analyze_text_jlpt(text_content)
        lex_time = time.time() - start_lex

        # Грамматика
        start_gram = time.time()
        grammar_level = await analyze_grammar_jlpt(text_content)
        gram_time = time.time() - start_gram

        total_time = time.time() - start_total
        text_len = len(text_content)

        full_report = (
            f"📊 <b>Оценка по JLPT:</b>\n\n"
            f"📘 <b>Лексика:</b>\n{jlpt_result}\n\n"
            f"📗 <b>Грамматика:</b>\n{grammar_level}"
        )

        log_execution_time(text_content, text_len, lex_time, gram_time, total_time, grammar_level)

        try:
            await loading_msg.delete()
        except Exception:
            pass
        await send_long_message(message, full_report)

    except Exception as e:
        try:
            await loading_msg.delete()
        except Exception:
            pass
        print(f"Ошибка при анализе текста: {e}")
        await message.answer("❌ Произошла ошибка при анализе текста.")
