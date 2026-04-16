from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
)
from datetime import datetime

from .base import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_new_words_date = Column(DateTime, nullable=True)
    words_per_day = Column(Integer, default=5)
    translation_language = Column(String, default="ru")


class DictionaryWord(Base):
    __tablename__ = "dictionary_words"
    id = Column(Integer, primary_key=True)
    surface = Column(String, nullable=False)
    reading = Column(String)
    meaning_en = Column(String)
    meaning = Column(String)
    jlpt_level = Column(String)
