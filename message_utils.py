from aiogram.types import Message
from typing import List, Optional
MAX_MESSAGE_LENGTH = 4000


async def send_long_message(message: Message, text: str, parse_mode: str = "HTML") -> List[int]:
    """
    Разбивает длинный текст на части и отправляет их по очереди.
    Возвращает список ID отправленных сообщений.
    """
    if len(text) <= MAX_MESSAGE_LENGTH:
        sent = await message.answer(text, parse_mode=parse_mode)
        return [sent.message_id]

    parts = []
    current_part = ""

    for line in text.split('\n'):
        if len(current_part) + len(line) + 1 > MAX_MESSAGE_LENGTH:
            if current_part:
                parts.append(current_part)
            current_part = line
        else:
            if current_part:
                current_part += "\n" + line
            else:
                current_part = line

    if current_part:
        parts.append(current_part)

    msg_ids = []
    for part in parts:
        if part.strip():
            try:
                sent = await message.answer(part, parse_mode=parse_mode)
                msg_ids.append(sent.message_id)
            except Exception:
                pass

    return msg_ids


import time
import os
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from datetime import datetime

TIMING_LOG_DIR = "../data"
TIMING_LOG_FILE = os.path.join(TIMING_LOG_DIR, "response_times.log")


def ensure_log_dir():
    if not os.path.exists(TIMING_LOG_DIR):
        os.makedirs(os.path.dirname(TIMING_LOG_DIR))


def get_real_handler_name(handler):
    """Пытается получить читаемое имя хэндлера"""

    # 1. Если handler - это объект HandlerObject из aiogram (часто бывает в мидлварях)
    if hasattr(handler, 'callback'):
        func = handler.callback
    else:
        func = handler

    # 2. Проверяем стандартное имя
    name = getattr(func, '__name__', 'Unknown')

    # 3. Если имя 'call', 'wrapper' или 'wrapped', пытаемся найти оригинал
    if name in ['call', 'wrapper', 'wrapped', 'async_wrapper']:
        # Иногда aiogram кладет оригинальную функцию в __wrapped__
        if hasattr(func, '__wrapped__'):
            original = func.__wrapped__
            return getattr(original, '__name__', name)

        # Если нет __wrapped__, посмотрим на модуль.
        # Если модуль не внутренний (не aiogram), то имя может быть полезным даже если оно странное
        module = getattr(func, '__module__', '')
        if 'aiogram' not in module:
            return name

    return name


class TimingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        # Используем perf_counter для высокой точности коротких интервалов
        start_time = time.perf_counter()

        # Выполняем сам хэндлер (функцию, которую вызвал пользователь)
        result = await handler(event, data)

        end_time = time.perf_counter()
        duration = end_time - start_time

        handler_name = get_real_handler_name(handler)

        # Определяем тип события и пользователя
        if isinstance(event, Message):
            event_type = "Msg"
            user_id = event.from_user.id
            # Можно добавить текст команды, если это сообщение
            if hasattr(event, 'text') and event.text:
                cmd_preview = event.text.split()[0] if event.text else ""
            else:
                cmd_preview = ""
        elif isinstance(event, CallbackQuery):
            event_type = "Cb"
            user_id = event.from_user.id
            cmd_preview = event.data[:25] if event.data else ""  # Первые 15 символов данных колбэка
        else:
            event_type = "Other"
            user_id = "N/A"
            cmd_preview = ""

        # Формируем строку лога
        log_entry = (
            f"[{datetime.now().strftime('%H:%M:%S')}] "
            f"User: {user_id} | "
            f"Type: {event_type} | "
            f"Cmd/Data: {cmd_preview} | "
            f"Handler: {handler_name} | "
            f"Time: {duration:.5f}s\n"
        )

        ensure_log_dir()
        with open(TIMING_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)

        return result