from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import uuid
import json
import re
import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

app = Flask(__name__)
CORS(app)

# Берем ключ из переменной окружения
GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")

if not GIGACHAT_API_KEY:
    print("=" * 50)
    print("❌ ОШИБКА: Не найден API ключ GIGACHAT_API_KEY")
    print("💡 На Render: добавьте переменную окружения в разделе Environment")
    print("💡 Локально: создайте файл .env и напишите: GIGACHAT_API_KEY=ваш_ключ")
    print("=" * 50)

ACCESS_TOKEN = None

def get_gigachat_token():
    global ACCESS_TOKEN
    try:
        url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Basic {GIGACHAT_API_KEY}"
        }
        data = "scope=GIGACHAT_API_PERS"
        
        print("🔄 Получение токена...")
        response = requests.post(url, headers=headers, data=data, verify=False)
        
        if response.status_code == 200:
            ACCESS_TOKEN = response.json()["access_token"]
            print("✅ Токен получен!")
            return ACCESS_TOKEN
        else:
            print(f"❌ Ошибка получения токена: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def call_gigachat(prompt):
    global ACCESS_TOKEN
    
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
                {"role": "system", "content": "Ты эксперт по 3D печати. Отвечай только JSON массивом."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.8,
            "max_tokens": 2000
        }
        
        response = requests.post(url, headers=headers, json=payload, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                return json.loads(json_match.group(0))
        elif response.status_code == 401:
            ACCESS_TOKEN = None
            return call_gigachat(prompt)
        
        return None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/generate_quiz', methods=['POST'])
def generate_quiz():
    print("📨 Получен запрос на генерацию")
    try:
        data = request.json
        difficulty = data.get('difficulty', 'medium')
        
        difficulty_text = {
            "easy": "начального уровня",
            "medium": "среднего уровня",
            "hard": "экспертного уровня"
        }
        
        prompt = f"""Сгенерируй 3 вопроса о 3D печати {difficulty_text[difficulty]}.
Верни ТОЛЬКО JSON массив. Каждый вопрос имеет поля:
- question (текст вопроса)
- options (массив из 4 вариантов)
- correct (индекс правильного ответа 0-3)
- explanation (объяснение)

Пример: [{{"question": "Что такое PLA?", "options": ["Пластик", "Металл", "Дерево", "Стекло"], "correct": 0, "explanation": "PLA - это пластик"}}]"""
        
        questions = call_gigachat(prompt)
        
        if questions:
            return jsonify({"success": True, "questions": questions})
        else:
            return jsonify({"success": False, "error": "Ошибка генерации"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 ЗАПУСК СЕРВЕРА")
    print("=" * 50)
    print("📍 Откройте в браузере: http://localhost:5001")
    print("💡 Нажмите Ctrl+C для остановки")
    print("-" * 50)
    
    get_gigachat_token()
    app.run(host='0.0.0.0', port=5001, debug=False)
