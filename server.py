from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
import json
import re
import os
from dotenv import load_dotenv

# ЗАГРУЖАЕМ ПЕРЕМЕННЫЕ ИЗ .env (только для локальной разработки)
load_dotenv()

app = Flask(__name__)
CORS(app)

# БЕРЁМ КЛЮЧ ТОЛЬКО ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
# НЕТ запасного ключа в коде! НЕТ хардкода!
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    print("=" * 50)
    print("❌ ОШИБКА: Не найден API ключ OPENROUTER_API_KEY")
    print("💡 Локально: создайте файл .env с содержимым:")
    print("   OPENROUTER_API_KEY=sk-or-v1-...")
    print("💡 На Render: добавьте переменную окружения в разделе Environment")
    print("=" * 50)

def call_venice_llm(prompt):
    """Вызов бесплатной Venice модели через OpenRouter"""
    if not OPENROUTER_API_KEY:
        return None
    
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
        
        response = client.chat.completions.create(
            model="cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            messages=[
                {"role": "system", "content": "Ты эксперт по 3D печати. Отвечай только JSON массивом."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            return json.loads(json_match.group(0))
        return None
        
    except Exception as e:
        print(f"❌ Ошибка вызова Venice: {e}")
        return None

def generate_quiz_questions(difficulty):
    difficulty_text = {
        "easy": "начального уровня",
        "medium": "среднего уровня",
        "hard": "экспертного уровня"
    }
    
    prompt = f"""Сгенерируй 3 вопроса о 3D печати {difficulty_text[difficulty]}.
Верни ТОЛЬКО JSON массив. Каждый вопрос имеет поля:
- question
- options (массив из 4 вариантов)
- correct (0-3)
- explanation

Пример: [{{"question": "Что такое PLA?", "options": ["Пластик", "Металл", "Дерево", "Стекло"], "correct": 0, "explanation": "PLA - это пластик"}}]"""
    
    return call_venice_llm(prompt)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/health')
def health():
    return jsonify({"status": "ok", "api_ready": OPENROUTER_API_KEY is not None})

@app.route('/generate_quiz', methods=['POST'])
def generate_quiz():
    if not OPENROUTER_API_KEY:
        return jsonify({"success": False, "error": "API ключ не настроен"}), 500
    
    try:
        data = request.json
        difficulty = data.get('difficulty', 'medium')
        questions = generate_quiz_questions(difficulty)
        
        if questions:
            return jsonify({"success": True, "questions": questions})
        else:
            return jsonify({"success": False, "error": "Ошибка генерации"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 ЗАПУСК СЕРВЕРА")
    print("📍 http://localhost:5001")
    print("-" * 50)
    app.run(host='0.0.0.0', port=5001, debug=False)
