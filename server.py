from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import uuid
import json
import re
import os
from dotenv import load_dotenv

# ЗАГРУЖАЕМ ПЕРЕМЕННЫЕ ИЗ .env (только для локальной разработки)
load_dotenv()

app = Flask(__name__)
CORS(app)

# Берём ключ ТОЛЬКО из переменных окружения
GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")

if not GIGACHAT_API_KEY:
    print("=" * 50)
    print("❌ ОШИБКА: Не найден API ключ GIGACHAT_API_KEY")
    print("💡 Локально: создайте файл .env с содержимым:")
    print("   GIGACHAT_API_KEY=ваш_ключ")
    print("💡 На Render: добавьте переменную окружения в разделе Environment")
    print("=" * 50)

ACCESS_TOKEN = None

def get_gigachat_token():
    """Получение токена доступа к GigaChat API"""
    global ACCESS_TOKEN
    if not GIGACHAT_API_KEY:
        return None
    try:
        url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Basic {GIGACHAT_API_KEY}"
        }
        data = "scope=GIGACHAT_API_PERS"
        
        print("🔄 Получение токена GigaChat...")
        response = requests.post(url, headers=headers, data=data, verify=False)
        
        if response.status_code == 200:
            ACCESS_TOKEN = response.json()["access_token"]
            print("✅ Токен GigaChat получен успешно")
            return ACCESS_TOKEN
        else:
            print(f"❌ Ошибка получения токена: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def call_gigachat(prompt):
    """Вызов GigaChat API для генерации вопросов"""
    global ACCESS_TOKEN
    
    if not GIGACHAT_API_KEY:
        return None
    
    if not ACCESS_TOKEN:
        ACCESS_TOKEN = get_gigachat_token()
        if not ACCESS_TOKEN:
            return None
    
    try:
        url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {ACCESS_TOKEN}"
        }
        
        payload = {
            "model": "GigaChat",
            "messages": [
                {"role": "system", "content": "Ты эксперт по 3D печати. Отвечай только JSON массивом. Никакого другого текста."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.8,
            "max_tokens": 2000
        }
        
        # ВАЖНО: verify=False отключает проверку SSL-сертификата
        response = requests.post(url, headers=headers, json=payload, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                return json.loads(json_match.group(0))
            return None
        elif response.status_code == 401:
            ACCESS_TOKEN = None
            return call_gigachat(prompt)
        else:
            print(f"❌ Ошибка API: {response.status_code}")
            print(f"Ответ: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка вызова GigaChat: {e}")
        return None

def generate_quiz_questions(difficulty):
    """Генерация 3 вопросов для викторины"""
    difficulty_text = {
        "easy": "начального уровня (базовые знания о 3D печати: PLA, ABS, основы слайсинга)",
        "medium": "среднего уровня (опытный пользователь: калибровка, ретракты, поддержки)",
        "hard": "экспертного уровня (сложные технические нюансы, химия материалов)"
    }
    
    prompt = f"""Сгенерируй 3 интересных вопроса о 3D печати {difficulty_text[difficulty]}.

Верни ТОЛЬКО JSON массив из 3 объектов. Каждый объект должен содержать поля:
- question: текст вопроса
- options: массив из 4 вариантов ответа
- correct: число от 0 до 3 (индекс правильного ответа)
- explanation: подробное объяснение почему ответ правильный (2-3 предложения)

Пример формата:
[
  {{
    "question": "Что означает PLA?",
    "options": ["Полилактид", "Полиэтилен", "Полиамид", "Полиуретан"],
    "correct": 0,
    "explanation": "PLA (полилактид) - биоразлагаемый пластик на основе кукурузного крахмала, самый популярный материал для начинающих."
  }}
]

Вопросы должны быть разнообразными: материалы, настройки слайсера, калибровка, пост-обработка, типы принтеров."""
    
    return call_gigachat(prompt)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/health')
def health():
    return jsonify({"status": "ok", "api_ready": GIGACHAT_API_KEY is not None})

@app.route('/generate_quiz', methods=['POST'])
def generate_quiz():
    if not GIGACHAT_API_KEY:
        return jsonify({"success": False, "error": "API ключ не настроен"}), 500
    
    print("📨 Получен запрос на генерацию викторины")
    try:
        data = request.json
        difficulty = data.get('difficulty', 'medium')
        
        questions = generate_quiz_questions(difficulty)
        
        if questions and len(questions) >= 3:
            print(f"✅ Сгенерировано {len(questions)} вопросов")
            return jsonify({"success": True, "questions": questions[:3]})
        else:
            return jsonify({"success": False, "error": "Ошибка генерации вопросов"}), 500
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 ЗАПУСК СЕРВЕРА С GIGACHAT")
    print("=" * 50)
    print("📍 Откройте в браузере: http://localhost:5001")
    print("🤖 Модель: GigaChat (Сбер)")
    print("-" * 50)
    
    if GIGACHAT_API_KEY:
        print("✅ API ключ найден")
        get_gigachat_token()
    else:
        print("⚠️ ВНИМАНИЕ: API ключ не найден!")
    
    app.run(host='0.0.0.0', port=5001, debug=False)
