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

# параметры по умолчанию для алгоритма fsrs
DEFAULT_PARAMS = [
    0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001, 1.8722, 0.1666, 0.796,
    1.4835, 0.0614, 0.2629, 1.6483, 0.6014, 1.8729, 0.5425, 0.0912, 0.0658, 0.1542
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
