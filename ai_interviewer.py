import json
from functools import lru_cache
from typing import List, Tuple, Optional, Dict, Any
from openai import OpenAI

_SCIBOX_CLIENT = None


def setup_scibox(api_key: str) -> None:
    global _SCIBOX_CLIENT
    _SCIBOX_CLIENT = OpenAI(api_key=api_key.strip(), base_url="https://llm.t1v.scibox.tech/v1", timeout=20.0)


@lru_cache(maxsize=128)
def _get_history(topic: str) -> List[Dict[str, str]]:
    return [{
        "role": "system",
        "content": (
                "/no_think Ты — технический интервьюер в BigTech. Тема: " + topic + ".\n"
                                                                                    "Правила:\n"
                                                                                    "- Никогда не здоровайся, если диалог уже начат.\n"
                                                                                    "- Не используй markdown, **жирный**, *курсив*, списки, <think>.\n"
                                                                                    "- Задавай вопросы кратко, по одному за раз, без преамбул.\n"
                                                                                    "- Не объясняй правила — просто спрашивай.\n"
                                                                                    "- При «ОЦЕНИТЬ КАНДИДАТА» — ТОЛЬКО JSON, без текста до/после."
        )
    }]


def _parse_eval(text: str) -> Optional[Dict]:
    s = text.find('{')
    e = text.rfind('}')
    if s == -1 or e == -1 or e <= s:
        return None
    try:
        d = json.loads(text[s:e + 1])
        if isinstance(d.get('score'), int) and 1 <= d['score'] <= 10 and isinstance(d.get('criteria'), dict):
            return d
    except:
        pass
    return None


def interview_step(topic: str, user_input: str) -> Tuple[str, Optional[Dict]]:
    hist = _get_history(topic)
    hist.append({"role": "user", "content": user_input.strip()})

    try:
        r = _SCIBOX_CLIENT.chat.completions.create(
            model="qwen3-32b-awq",
            messages=hist,
            temperature=0.1,
            top_p=0.85,
            max_tokens=400,
            stream=False
        )
        reply = r.choices[0].message.content.strip()
        hist.append({"role": "assistant", "content": reply})

        if user_input.strip() == "ОЦЕНИТЬ КАНДИДАТА":
            return reply, _parse_eval(reply)
        return reply, None

    except Exception as ex:
        msg = f"[Ошибка] {str(ex)}"
        hist.append({"role": "assistant", "content": msg})
        return msg, None