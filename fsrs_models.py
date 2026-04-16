from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from datetime import datetime, timezone
from .base import Base


class CustomWord(Base):
    __tablename__ = "custom_words"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    surface = Column(String, nullable=False)
    reading = Column(String, nullable=True)
    meaning = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FSRSCard(Base):
    __tablename__ = "fsrs_cards"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(Integer, nullable=False)
    word_type = Column(String, default="dict")  # dict / custom

    # Состояние памяти FSRS
    stability = Column(Float, default=0.0)
    difficulty = Column(Float, default=5.0)

    # Временные метки (UTC)
    last_review = Column(DateTime, nullable=True)
    due = Column(DateTime, nullable=False)

    # Статистика
    reps = Column(Integer, default=0)
    lapses = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))