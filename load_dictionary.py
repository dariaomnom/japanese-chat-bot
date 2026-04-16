import csv
from sqlalchemy import select
from ..db.base import AsyncSessionLocal
from ..db.models import DictionaryWord


async def load_dictionary():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(DictionaryWord))
        if result.first():
            return
        with open("bot/data/jlpt_vocab.csv", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            words = []
            for row in reader:
                word = DictionaryWord(
                    surface=row["Original"],
                    reading=row["Furigana"],
                    meaning_en=row["English"],
                    meaning=row["Russian"],
                    jlpt_level=row["JLPT Level"],
                )
                words.append(word)
            session.add_all(words)
            await session.commit()
        print("Dictionary loaded")