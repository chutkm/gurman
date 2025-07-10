import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

SYSTEM_PROMPT = """
Ты — дружелюбный ресторанный гид в Москве. Отвечай на вопросы пользователей, помогая им выбрать ресторан.
Учитывай предпочтения по кухне, атмосфере, количеству человек и другим параметрам.Всегда отвечай на русском языке.Отвечай буквально 5 предложениями!И говори правду.Когда советуешь ресторан,присылай ссылку сайта этого ресторана,которая действительно существует!!!
"""

def ask_llm_ollama(user_message: str, model: str = "qwen3") -> str:
    prompt = f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\nОтвечай на русском языке. {user_message}\n<|assistant|>"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
    except Exception as e:
        return f"⚠️ Ошибка при обращении к Ollama: {e}"
