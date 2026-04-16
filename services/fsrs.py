import fsrs
from datetime import datetime, timezone
from typing import Optional

Scheduler = fsrs.Scheduler
Card = fsrs.Card
Rating = fsrs.Rating

RATING_MAP = {
    "again": Rating.Again,
    "hard": Rating.Hard,
    "good": Rating.Good,
    "easy": Rating.Easy,
}

# парамеиры по умолчанию для алгоритма fsrs
DEFAULT_PARAMS = [
    0.4783, 1.2172, 9.7398, 15.8796, 6.8942, 0.3659, 3.2729, 0.0099, 1.4107,
    0.0061, 0.5899, 1.68, 0.009, 0.4049, 1.2676, 0.0, 3.0064, 0.3535, 0.5764,
    0.2246, 0.2205
]


class FSRSEngine:
    def __init__(self, params: Optional[list] = None):
        self.engine = Scheduler(params or DEFAULT_PARAMS)

    def repeat(self, card, now: datetime, rating):
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        new_card, _ = self.engine.review_card(card, rating, now)
        return new_card

    @staticmethod
    def card_to_dict(card) -> dict:
        return {
            "stability": card.stability,
            "difficulty": card.difficulty,
            "last_review": card.last_review,
            "due": card.due,
        }

    @staticmethod
    def dict_to_card(stability: float, difficulty: float,
                     last_review: Optional[datetime], due: datetime):
        card = Card()
        card.stability = stability if stability > 0.0 else 0.1
        card.difficulty = difficulty

        if last_review is not None and last_review.tzinfo is None:
            last_review = last_review.replace(tzinfo=timezone.utc)
        card.last_review = last_review

        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        card.due = due

        return card


fsrs_engine = FSRSEngine()
