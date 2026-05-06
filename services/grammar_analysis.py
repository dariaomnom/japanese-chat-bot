import os
import httpx
import traceback
from dotenv import load_dotenv

load_dotenv()

AMVERA_TOKEN = os.getenv("AMVERA_API_TOKEN")
MODEL = "qwen"
MODEL_NAME = "qwen3_30b"
BASE_URL = "https://kong-proxy.yc.amvera.ru/api/v1"


SYSTEM_PROMPT = """
You are a strict JLPT Grammar Classifier. Your task is to assign the SINGLE most accurate JLPT level (N5, N4, N3, N2, N1) to the provided Japanese text based SOLELY on its grammatical structures.
CRITICAL INSTRUCTIONS:
1. IGNORE VOCABULARY: Do not let rare Kanji, complex nouns, or specialized vocabulary influence the level. Focus ONLY on particles, conjugations, auxiliary verbs, and sentence patterns.
2. MAXIMUM LEVEL RULE: The text's level is determined by the HIGHEST level grammar point present. If an N1 structure is used correctly, the text is N1, regardless of how simple the rest is.
3. CONTEXTUAL DISAMBIGUATION:
   - For common particles (e.g., 'ni', 'de', 'to'), determine if they are used in a basic sense (N5/N4) or an abstract/idiomatic sense (N3+).
   - Example: 'Ni' as destination is N5. 'Ni atatte' (on the occasion of) is N2. 'Ni itaru' (to reach/conclude) is N1.
4. AVOID OVER-ESTIMATION FOR LOW LEVELS:
   - Simple sentences with multiple N5 particles are still N5.
   - Do not upgrade to N4 unless you see specific N4 markers like: Passive/Causative forms, ba/tara/nara conditionals, hou ga ii, koto/no nominalization in complex roles, or humble/honorific verbs (`irassharu`, `itasu`).
5. AVOID UNDER-ESTIMATION FOR HIGH LEVELS:
   - Look for specific N1/N2 markers that have no direct N3/N4 equivalent.
   - N1 Markers: Archaic forms (`bekarazu`, ga hayai ka`), complex logical connectors (`ikan ni kakawarazu, ni soku shite`), emphatic/negative idioms (`wa oroka, `node wa arumai shi`).
   - N2 Markers: Formal written style (`ni saishite`, ni motozuite`), nuanced expressions (`bakari ni, dake atte`), complex conditionals (`to shitemo, `ni seyo`).

REFERENCE GRAMMAR POINTS (Non-exhaustive but indicative):
- N5: Basic particles (wa, ga, o, ni, de), masu/te-forms, simple adjectives, existence (aru/iru), basic questions.
- N4: Passive/Causative, Potential form, Conditionals (ba, tara, nara), koto/no nominalization, hou ga ii, wake da (basic), humble/honorific basics.
- N3: Nuanced conjunctions (`noni`, node`), `tame ni (purpose/reason), ni yotte (by means of), ni tsuite, ni taishite, wake dewa nai, hazu da.
- N2: Formal/Abstract connectors (`ni atatte`, ni saishite, ni motozuite`), `bakari ni, dake atte, ni kagiru, ni chigainai, to iu wake da, complex passive/causative nuances.
- N1: Literary/Archaic/Idiomatic (`bekarazu`, ga hayai ka, ikan ni kakawarazu, ni soku shite, wa oroka, node wa arumai shi, ni itaru, `o motte`), highly abstract logic.

OUTPUT FORMAT:
Return ONLY the level string: "N5", "N4", "N3", "N2", or "N1".
No explanation. No punctuation.

EXAMPLES FOR CALIBRATION:
Text: "私は毎日学校へ行きます。" -> N5
Text: "食べさせられたくなかった。" -> N4 (Causative-Passive)
Text: "雨なのに、彼は来ました。" -> N3 (noni)
Text: "参加するにあたって、準備が必要です。" -> N2 (ni atatte)
Text: "彼の実力はいかんにかかわらず、挑戦すべきだ。" -> N1 (ikan ni kakawarazu)
"""


async def analyze_grammar_jlpt(text: str) -> str:
    # url = f"{BASE_URL}/models/{MODEL_NAME}/chat/completions"
    url = f"{BASE_URL}/models/{MODEL}"

    headers = {
        "X-Auth-Token": f"Bearer {AMVERA_TOKEN}",
        "Content-Type": "application/json"
    }

    full_prompt = f"{SYSTEM_PROMPT}\n\nText to analyze: {text}"

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "text": full_prompt
            }
        ],
        "max_tokens": 5,
        "temperature": 0
    }

    try:
        print(f"Запрос к Amvera ({MODEL_NAME})")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)

            if resp.status_code != 200:
                print(f"HTTP Error {resp.status_code}: {resp.text[:300]}")
                return "Ошибка API"

            data = resp.json()
            print(f"Ответ API: {str(data)[:300]}...")

            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                message = choice.get("message", {})

                result_text = message.get("content", "").strip()
                if not result_text:
                    result_text = message.get("text", "").strip()

                print(f"Raw Response: '{result_text}'")

                for level in ["N5", "N4", "N3", "N2", "N1"]:
                    if level in result_text:
                        return level

                return "N/A"
            else:
                print("Нет choices в ответе")
                return "Пустой ответ"

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Исключение:\n{error_trace}")
        return "Попробуйте позже"
