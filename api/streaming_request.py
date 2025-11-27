import requests, json, os
TOKEN = "sk-gqlpOmmxNrBvLyv766GXYg"
URL = "https://llm.t1v.scibox.tech/v1/chat/completions"
MODEL_NAME = "qwen3-32b-awq"
MESSAGES_PAYLOAD = [
    {"role": "system", "content": "Ты дружелюбный помощник"},
    {"role": "user", "content": "Расскажи анекдот"}
]
REQUEST_BODY = {
    "model": MODEL_NAME,
    "messages": MESSAGES_PAYLOAD,
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 256,
    "stream": True
}
def send_qwen_request():
    """Отправляет POST-запрос к Qwen API и печатает ответ в потоковом режиме."""
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        # Отправка запроса с stream=True для обработки потока данных
        response = requests.post(
            URL, 
            headers=headers, 
            data=json.dumps(REQUEST_BODY),
            stream=True #
        )
        response.raise_for_status() 
        for line in response.iter_lines():
            if line:
                try:
                    if line.startswith(b"data: "):
                        data_chunk = line.decode('utf-8')[6:].strip()

                        if data_chunk == "[DONE]":
                            break
                        
                        data = json.loads(data_chunk)
                        
                        delta = data['choices'][0]['delta']
                        
                        if 'content' in delta:
                            content = delta['content']
                            print(content, end="", flush=True) 

                except json.JSONDecodeError:
                    continue
                except KeyError as e:
                    print(f"\n[ОШИБКА ПАРСИНГА: Отсутствует ключ {e} в фрагменте JSON]")
                    break
            
    except requests.exceptions.RequestException as e:
        print(f"\nОШИБКА API (код {response.status_code if 'response' in locals() else 'нет ответа'}):")
        print(f"Не удалось подключиться или получить ответ. Детали: {e}")
        if 'response' in locals():
             print(f"Текст ответа: {response.text}")
        return None
    except Exception as e:
        print(f"НЕИЗВЕСТНАЯ ОШИБКА: {e}")
        return None

if __name__ == "__main__":
    send_qwen_request()