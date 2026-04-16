import os
import httpx
from dotenv import load_dotenv

load_dotenv()
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
# MODEL = "openrouter/free"
MODEL = "arcee-ai/trinity-large-preview:free"

SYSTEM_PROMPT = """
You are a Japanese grammar evaluator. Assess the JLPT grammar level (N5-N1) of the given text.
Rules:
- Only evaluate grammar, ignore vocabulary.
Output: ONLY a single JLPT level (N5, N4, N3, N2, N1). No explanation.
"""


async def analyze_grammar_jlpt(text: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        "max_tokens": 20,
        "temperature": 0
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    print("DEBUG: OpenRouter response:", data)

    result = data["choices"][0]["message"]["content"].strip()
    for level in ["N5", "N4", "N3", "N2", "N1"]:
        if level in result:
            return level

    return "N/A"
