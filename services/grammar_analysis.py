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
You are a Japanese grammar evaluator. Assess the JLPT grammar level (N5-N1) of the given text.
Rules:
- Only evaluate grammar structures (particles, conjugations, auxiliary verbs).
- Ignore vocabulary complexity.
Output: ONLY a single JLPT level (N5, N4, N3, N2, N1). No explanation.
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
