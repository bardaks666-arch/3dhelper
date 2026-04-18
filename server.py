from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Берём ключ из переменных окружения
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    print("❌ ОШИБКА: Не найден API ключ OPENROUTER_API_KEY")
    print("💡 Добавьте переменную окружения на Render или создайте файл .env")

def call_venice_llm(prompt):
    """Вызов бесплатной Venice модели через OpenRouter"""
    if not OPENROUTER_API_KEY:
        return None
    
    try:
        # Создаём клиент, совместимый с OpenAI API
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
        
        # Дополнительные заголовки для идентификации приложения [citation:9]
        extra_headers = {
            "HTTP-Referer": "https://3dhelper.onrender.com",  # ваш сайт
            "X-Title": "3D Hub Pro"  # название приложения
        }
        
        response = client.chat.completions.create(
            model="cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            messages=[
                {
                    "role": "system", 
                    "content": "Ты эксперт по 3D печати. Отвечай только JSON массивом. Никакого другого текста."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=2000,
            extra_headers=extra_headers
        )
        
        content = response.choices[0].message.content
        
        # Извлекаем JSON из ответа
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            return json.loads(json_match.group(0))
        return None
        
    except Exception as e:
        print(f"❌ Ошибка вызова Venice: {e}")
        return None

# Функция для генерации вопросов
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
    print("🚀 ЗАПУСК СЕРВЕРА С OPENROUTER (VENICE)")
    print("=" * 50)
    print("📍 Откройте в браузере: http://localhost:5001")
    print("🤖 Модель: Dolphin Mistral 24B Venice Edition (бесплатно)")
    print("-" * 50)
    
    if OPENROUTER_API_KEY:
        print("✅ API ключ найден")
    else:
        print("⚠️ ВНИМАНИЕ: API ключ не найден!")
    
    app.run(host='0.0.0.0', port=5001, debug=False)
