from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional
from openai import OpenAI


class TaskGenerator:
    """
    Генерация задач, эталонных решений и ревью кода с помощью qwen3-моделей.
    Ожидается OpenAI-совместимый API (base_url указывает на прокси с qwen3).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "qwen3-coder-30b-a3b-instruct-fp8",
    ) -> None:
        api_key = api_key
        if not api_key:
            raise ValueError("API key не передан и не найден в переменной окружения OPENAI_API_KEY")

        # base_url — обязателен для работы с кастомным хостом qwen3
        base_url = base_url
        if not base_url:
            raise ValueError("base_url не передан и не найден в переменной окружения OPENAI_BASE_URL")

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.task_cache: Dict[str, Dict[str, Any]] = {}
        self.task_cache: Dict[str, Dict[str, Any]] = {}
        self.max_history = 5

        self.difficulty_levels: Dict[str, Dict[str, Any]] = {
            "junior": {
                "description": "Начальный уровень",
                "max_tokens": 300,
                "temperature": 0.7,
            },
            "middle": {
                "description": "Средний уровень",
                "max_tokens": 500,
                "temperature": 0.5,
            },
            "senior": {
                "description": "Продвинутый уровень",
                "max_tokens": 700,
                "temperature": 0.3,
            },
        }

    # ========= Вспомогательные методы =========

    def _chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float = 0.5,
    ) -> str:
        """Один вызов LLM, возвращает только текст контента."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()

    @staticmethod
    def _safe_json_loads(raw: str) -> Any:
        """
        Пытается распарсить JSON, убирая возможные markdown-обёртки ... ```.
        """
        text = raw.strip()

        # Убираем возможные тройные кавычки с языком/без
        if text.startswith("```"):
            text = text.strip("`")
        first_brace = min(
            (i for i in [text.find("{"), text.find("[")] if i != -1),
            default=-1,
        )
        if first_brace > 0:
            text = text[first_brace:]

        return json.loads(text)

    # ========= Основной функционал =========

    def generate_task(self, position: str, difficulty: str = "middle") -> Dict[str, Any]:
        """
        Генерирует coding task на указанную позицию и сложность.
        Возвращает dict с ключами: id, description, constraints, test_cases.
        """
        difficulty_config = self.difficulty_levels.get(
            difficulty, self.difficulty_levels["middle"]
        )

        # Берём несколько последних задач, чтобы модель не повторяла темы
        recent_tasks = list(self.task_cache.values())[-self.max_history:]
        recent_summaries = [
            f"- id: {t.get('id', '?')} | {t.get('description', '').splitlines()[0][:120]}"
            for t in recent_tasks
            if "description" in t
        ]
        recent_block = "\n".join(recent_summaries) if recent_summaries else "нет"

        system_prompt = (
            "Ты эксперт по созданию тестовых заданий для IT-специалистов. "
            "ВСЕГДА отвечай строго валидным JSON, без комментариев, без markdown, без ```.\n"
            "Стремись делать каждую новую задачу тематически и по формулировке отличной от предыдущих."
        )

        user_prompt = f"""
    Создай одно НОВОЕ (отличающееся от прошлых) coding task для позиции: "{position}".
    Уровень сложности: "{difficulty}".

    Вот последние сгенерированные задачи (не повторяй их темы и формулировки буквально):
    {recent_block}

    Требования к задаче:
    - Конкретная техническая задача.
    - Время выполнения задачи не более 30 минут.
    - Четко описанные входные и выходные данные.
    - Набор тестовых случаев для проверки решения.

    Ограничения:
    - Задача должна быть независимой (всё, что нужно для решения — в условии).
    - Не используй внешние API и базы данных.

    Формат ответа (строго валидный JSON, без пояснений и комментариев):

    {{
      "id": "уникальный_идентификатор_задачи",
      "description": "Подробная постановка задачи на русском языке",
      "constraints": "Ограничения по входным данным, времени и памяти (если есть)",
      "test_cases": [
        {{
          "input": "пример входных данных в удобном формате",
          "output": "ожидаемый результат"
        }}
      ]
    }}
            """.strip()

        try:
            content = self._chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=difficulty_config["max_tokens"],
                temperature=difficulty_config["temperature"],
            )
            task_data = self._safe_json_loads(content)

            if not isinstance(task_data, dict) or "id" not in task_data:
                raise ValueError("В ответе нет корректного поля 'id'")

            self.task_cache[task_data["id"]] = task_data
            return task_data

        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON при генерации задачи: {e}\nRAW:\n{content}")
            return {
                "error": "Ошибка генерации задачи (JSONDecodeError)",
                "raw_response": content,
                "position": position,
                "difficulty": difficulty,
            }
        except Exception as e:
            print(f"❌ Ошибка при генерации задачи: {e}")
            return {
                "error": str(e),
                "position": position,
                "difficulty": difficulty,
            }

    def generate_solutions(
        self,
        task_id: str,
        languages: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Генерирует эталонные решения для задачи на нескольких языках.
        languages: список из {"python", "cpp", "java", "go"} и т.п.
        Возвращает JSON с полем "solutions": {lang: "код"}.
        """
        task = self.task_cache.get(task_id)
        if not task:
            return {"error": f"Задача с id={task_id} не найдена"}

        if languages is None:
            languages = ["python", "cpp", "java", "go"]

        system_prompt = (
            "Ты опытный разработчик и автор эталонных решений для задач программирования. "
            "ВСЕГДА отвечай строго валидным JSON, без markdown и без ```."
        )

        user_prompt = f"""
Описание задачи:
{task.get("description", "")}

Ограничения:
{task.get("constraints", "")}

Тестовые случаи:
{json.dumps(task.get("test_cases", []), ensure_ascii=False, indent=2)}

Сгенерируй эталонные решения задачи на следующих языках: {", ".join(languages)}.

Требования:
- Решения должны проходить приведённые тестовые случаи.
- Пиши чистый и понятный код.
- При необходимости, добавь минимальное пояснение в комментариях.

Формат ответа (строго валидный JSON):

{{
  "task_id": "{task_id}",
  "solutions": {{
    "python": "код решения на Python (если язык запрошен)",
    "cpp": "код решения на C++ (если язык запрошен)",
    "java": "код решения на Java (если язык запрошен)",
    "go": "код решения на Go (если язык запрошен)"
  }}
}}
        """.strip()

        try:
            content = self._chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=1500,
                temperature=0.4,
            )
            solutions_data = self._safe_json_loads(content)

            task.setdefault("solutions", {}).update(solutions_data.get("solutions", {}))
            self.task_cache[task_id] = task

            return solutions_data

        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON при генерации решений: {e}\nRAW:\n{content}")
            return {
                "error": "Ошибка генерации решений (JSONDecodeError)",
                "raw_response": content,
                "task_id": task_id,
                "languages": languages,
            }
        except Exception as e:
            print(f"❌ Ошибка при генерации решений: {e}")
            return {
                "error": str(e),
                "task_id": task_id,
                "languages": languages,
            }

    def review_code(
        self,
        task_id: str,
        user_code: str,
        language: str = "python",
    ) -> Dict[str, Any]:
        """
        Анализирует код пользователя относительно задачи и тест-кейсов.
        """
        task = self.task_cache.get(task_id)
        if not task:
            return {"error": f"Задача с id={task_id} не найдена"}

        system_prompt = (
            "Ты технический интервьюер и эксперт по коду. "
            "ВСЕГДА отвечай строго валидным JSON, без markdown и без ```."
        )

        user_prompt = f"""
Кандидату дана следующая задача:
{task.get("description", "")}

Тестовые случаи для проверки решения:
{json.dumps(task.get("test_cases", []), ensure_ascii=False, indent=2)}

Код кандидата на языке {language}:
```{language}
{user_code}Требуется:
1. Оценить корректность решения относительно условия.
2. Проверить решение на открытых тестах выше.
3. Дополнительно ПРИДУМАЙ САМ несколько скрытых тестовых случаев
(краевые случаи, большие данные, особые комбинации, невалидный ввод и т.п.).
Эти скрытые тесты ИСПОЛЬЗУЙ для оценки корректности, но НЕ ПОКАЗЫВАЙ их явно в ответе.
4. По результатам всех проверок (открытые + скрытые тесты) оцени временную и,
по возможности, пространственную сложность.
5. Оцени качество кода: стиль, читаемость, структурированность.
6. Укажи возможные проблемы по надёжности и безопасности (если применимо).
7. Дай краткий, но содержательный фидбек.

Формат ответа (строго валидный JSON):

{{
  "Correctness": "оценка корректности и краткое пояснение",
  "Efficiency": "оценка сложности и производительности",
  "CodeQuality": "оценка стиля и читаемости",
  "Safety": "оценка надёжности и потенциальных рисков",
  "TestsSummary": "проходят ли тестовые случаи и какие нет (если есть проблемы)",
  "Summary": "краткое общее резюме по решению"
}}
        """.strip()

        try:
            content = self._chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=600,
                temperature=0.3,
            )
            review_data = self._safe_json_loads(content)
            return review_data

        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON при ревью кода: {e}\nRAW:\n{content}")
            return {
                "error": "Ошибка ревью кода (JSONDecodeError)",
                "raw_response": content,
                "task_id": task_id,
            }
        except Exception as e:
            print(f"❌ Ошибка при проверке задачи: {e}")
            return {
                "error": str(e),
                "task_id": task_id,
            }


if __name__ == "__main__":
    # Пример использования — значения лучше передавать через env или конфиг
    generator = TaskGenerator(
        api_key="sk-gqlpOmmxNrBvLyv766GXYg",
        base_url="https://llm.t1v.scibox.tech/v1",
        model="qwen3-coder-30b-a3b-instruct-fp8",
    )

    # 1. Генерация задачи
    task = generator.generate_task(
        position="Backend development",
        difficulty="middle",
    )
    print("=== Сгенерированная задача ===")
    print(json.dumps(task, ensure_ascii=False, indent=2))

    if "id" not in task:
        raise SystemExit("Не удалось сгенерировать задачу (нет id).")

    task_id = task["id"]

    # 2. Генерация эталонных решений
    solutions = generator.generate_solutions(
        task_id=task_id,
        languages=["python", "cpp", "java", "go"],
    )
    print("=== Эталонные решения ===")
    print(json.dumps(solutions, ensure_ascii=False, indent=2))

    # 3. Пример: проверка кода кандидата
#     candidate_code = """
# def solve():
#     # Здесь должен быть код кандидата
#     pass
# """
#
#     review = generator.review_code(
#         task_id=task_id,
#         user_code=candidate_code,
#         language="python",
#     )
#     print("=== Ревью решения ===")
#     print(json.dumps(review, ensure_ascii=False, indent=2))