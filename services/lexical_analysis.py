from sudachipy import Dictionary
from sudachipy import tokenizer as sudachi_tokenizer
from wanakana import to_hiragana
from wanakana.utils import is_char_japanese

from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from collections import Counter

from ..db.models import DictionaryWord

JLPT_WEIGHTS = {"N5": 0, "N4": 1, "N3": 2, "N2": 3, "N1": 4}
STOP_POS = {"助詞", "助動詞", "記号", "補助記号", "括弧開", "括弧閉"}


class JLPTAnalyzer:
    def __init__(self, db_session: Session):
        self.db = db_session

        self.tokenizer = Dictionary().create()
        self.mode = sudachi_tokenizer.Tokenizer.SplitMode.C

    @staticmethod
    def _normalize_tilde(text: str) -> str:
        if not text:
            return ""
        return text.strip().lstrip('～~〰').rstrip('～~〰')

    @staticmethod
    def _parse_variants(db_value: str) -> list[str]:
        if not db_value:
            return []
        parts = db_value.replace(';', ',').split(',')
        return [p.strip() for p in parts if p.strip()]

    def _is_valid_token(self, token):
        pos = token.part_of_speech()
        main_pos = pos[0]
        if main_pos in STOP_POS:
            return False
        surface = token.surface().strip()
        if not surface or not any(is_char_japanese(char) for char in surface):
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
        seen_lemmas = set()

        for token in tokens:
            if not self._is_valid_token(token):
                continue

            surface = token.surface()
            lemma = token.dictionary_form()

            if not lemma or lemma in seen_lemmas:
                continue

            word_data = await self._lookup_word(lemma, surface, token)

            seen_lemmas.add(lemma)
            results.append({
                "surface": surface,
                "lemma": lemma,
                "jlpt": word_data.jlpt_level if word_data else "N/A",
            })

            if not word_data:
                print("MISS")
                print("lemma:", lemma)
                print("surface:", surface)
                print("reading:", token.reading_form())

        return results


    async def _lookup_word(self, lemma: str, surface: str, token=None):
        """
        Быстрый поиск слова в словаре по точному совпадению
        Если не найдено, то глубокий поиск
        """

        # Быстрый поиск
        stmt_fast = select(DictionaryWord).where(
            or_(
                DictionaryWord.surface == lemma,
                DictionaryWord.surface == surface,
                DictionaryWord.reading == lemma
            )
        )
        result_fast = await self.db.execute(stmt_fast)
        candidates_fast = result_fast.scalars().all()

        if candidates_fast:
            return self._get_easiest_word(candidates_fast)

        # Глубокий поиск
        clean_lemma = self._normalize_tilde(lemma)
        clean_surface = self._normalize_tilde(surface)

        targets = {lemma, surface, clean_lemma, clean_surface}
        if not lemma.startswith("～"): targets.add(f"～{clean_lemma}")
        if not surface.startswith("～"): targets.add(f"～{clean_surface}")
        targets.discard("")

        final_candidates = []

        conditions_surface = [DictionaryWord.surface.like(f"{t}%") for t in targets]
        if conditions_surface:
            stmt_like = select(DictionaryWord).where(or_(*conditions_surface))
            res_like = await self.db.execute(stmt_like)

            for word in res_like.scalars().all():
                variants = self._parse_variants(word.surface)
                if any(t in variants for t in targets):
                    final_candidates.append(word)

        if not final_candidates and token:
            reading_form = token.reading_form()
            if reading_form:
                pure_hiragana = to_hiragana(reading_form)
                clean_reading = self._normalize_tilde(pure_hiragana)

                read_targets = {pure_hiragana, clean_reading, lemma, clean_lemma}
                if not pure_hiragana.startswith("～"): read_targets.add(f"～{clean_reading}")
                read_targets.discard("")

                stmt_read_exact = select(DictionaryWord).where(
                    DictionaryWord.reading.in_(read_targets)
                )
                res_read = await self.db.execute(stmt_read_exact)
                read_candidates = list(res_read.scalars().all())

                if not read_candidates:
                    read_conditions = [DictionaryWord.reading.like(f"{t}%") for t in read_targets]
                    if read_conditions:
                        stmt_read_like = select(DictionaryWord).where(or_(*read_conditions))
                        res_read_like = await self.db.execute(stmt_read_like)
                        for word in res_read_like.scalars().all():
                            r_variants = self._parse_variants(word.reading)
                            if any(t in r_variants for t in read_targets):
                                read_candidates.append(word)

                final_candidates.extend(read_candidates)

        if final_candidates:
            return self._get_easiest_word(final_candidates)

        return None

    def _get_easiest_word(self, candidates):
        if not candidates:
            return None

        def get_weight(word):
            return JLPT_WEIGHTS.get(word.jlpt_level, 99)
        return min(candidates, key=get_weight)

    def _format_result(self, analyzed):
        jlpt_counts = Counter([x["jlpt"] for x in analyzed])
        lines = []
        found_any = False

        for x in analyzed:
            if x['jlpt'] != "N/A":
                if x['surface'] != x['lemma']:
                    lines.append(f"{x['surface']} ({x['lemma']}) - {x['jlpt']}")
                else:
                    lines.append(f"{x['surface']} - {x['jlpt']}")
                found_any = True

        if not found_any:
            lines.append("В тексте не найдено слов из словаря JLPT.")

        lines.append("\n📈 Статистика:")
        valid_counts = {level: count for level, count in jlpt_counts.items() if level != "N/A"}
        total_valid = sum(valid_counts.values())

        if total_valid == 0:
            lines.append("Нет распознанных слов")
            return "\n".join(lines)

        for level, count in sorted(valid_counts.items(), key=lambda x: x[1], reverse=True):
            percent = (count / total_valid) * 100
            lines.append(f"{level}: {count} ({percent:.0f}%)")

        return "\n".join(lines)
