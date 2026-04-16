from sudachipy import Dictionary
from sudachipy import tokenizer as sudachi_tokenizer
from wanakana.utils import is_char_japanese

from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from collections import Counter

from ..db.models import DictionaryWord


class JLPTAnalyzer:
    def __init__(self, db_session: Session):
        self.db = db_session

        self.tokenizer = Dictionary().create()
        self.mode = sudachi_tokenizer.Tokenizer.SplitMode.C

    def _is_valid_token(self, token):
        pos = token.part_of_speech()

        main_pos = pos[0]

        # токены, которые нужно пропустить: пунктуация, междометия, предлоги
        STOP_POS = {
            "助詞",
            "助動詞",
            "記号",
            # "感動詞",
            "補助記号",
            "括弧開",
            "括弧閉",
        }

        if main_pos in STOP_POS:
            return False

        surface = token.surface().strip()
        if not surface:
            return False
        if not any(is_char_japanese(char) for char in surface):
            return False

        return True

    async def analyze_text_jlpt(self, text: str):
        tokens = self._tokenize(text)
        analyzed = await self._analyze_tokens(tokens)
        return self._format_result(analyzed)

    def _tokenize(self, text: str):
        return list(self.tokenizer.tokenize(text, self.mode))

    async def _analyze_tokens(self, tokens):
        results = []

        for token in tokens:
            if not self._is_valid_token(token):
                continue

            surface = token.surface()
            lemma = token.dictionary_form()

            if not lemma:
                continue

            word_data = await self._lookup_word(lemma, surface)

            results.append({
                "surface": surface,
                "lemma": lemma,
                "jlpt": word_data.jlpt_level if word_data else "N/A",
                "meaning": word_data.meaning if word_data else None
            })

            if not word_data:
                print("MISS")
                print("lemma:", lemma)
                print("surface:", surface)
                print("reading:", token.reading_form())

        return results

    # поиск в словаре
    async def _lookup_word(self, lemma: str, surface: str):

        stmt = select(DictionaryWord).where(
            or_(
                DictionaryWord.surface == lemma,
                DictionaryWord.surface == surface,
                DictionaryWord.reading == lemma
            )
        )

        result = await self.db.execute(stmt)
        return result.scalars().first()

    def _format_result(self, analyzed):
        jlpt_counts = Counter([x["jlpt"] for x in analyzed])

        lines = []

        found_any = False
        for x in analyzed:
            if x['jlpt'] != "N/A":
                lines.append(
                    f"{x['surface']} ({x['lemma']}) - {x['jlpt']}"
                )
                found_any = True

        if not found_any:
            lines.append("В тексте не найдено слов из словаря JLPT.")

        lines.append("\n📈 Статистика:")
        valid_counts = {
            level: count
            for level, count in jlpt_counts.items()
            if level not in {"N/A"}
        }
        total_valid = sum(valid_counts.values())
        if total_valid == 0:
            lines.append("Нет распознанных слов")
            return "\n".join(lines)

        for level, count in sorted(valid_counts.items(), key=lambda x: x[1], reverse=True):
            percent = (count / total_valid) * 100
            lines.append(f"{level}: {count} ({percent:.1f}%)")

        return "\n".join(lines)
