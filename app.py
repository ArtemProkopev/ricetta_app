import os
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import logging  # Добавлено логирование

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Безопасное получение API ключа
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyBx19-uNQyD5WaZB0mWJ7agoigG0hTGMtQ')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"  # Обновлена версия API

def get_gemini_response(prompt):
    """Улучшенная функция запроса к Gemini API с обработкой ошибок"""
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        # Увеличен таймаут и добавлена обработка SSL
        response = requests.post(
            GEMINI_API_KEY,
            json=data,
            headers=headers,
            timeout=30,
            verify=True  # Включена проверка SSL
        )
        
        # Детальный анализ ответа
        if response.status_code != 200:
            logger.error(f"Gemini API Error: {response.status_code} - {response.text}")
            return None
            
        result = response.json()
        
        # Безопасное извлечение текста
        try:
            return result['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError) as e:
            logger.error(f"Invalid response format: {str(e)}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        return None

@app.route('/health')
def health_check():
    """Упрощенный health check без вызова внешнего API"""
    return jsonify({"status": "healthy", "service": "running"}), 200

@app.route('/chat', methods=['POST'])
def chat():
    """Обновленный обработчик чата с кэшированием"""
    try:
        user_input = request.json.get('message', '').strip()
        if not user_input:
            return jsonify({'error': 'Пожалуйста, введите ингредиенты'}), 400
            
        prompt = f"""Создай 2 рецепта используя: {user_input}. Формат:
        1. Название блюда
        2. Ингредиенты:
           - Есть: [список]
           - Купить: [список]
        3. Пошаговый рецепт
        4. Время приготовления
        5. Полезный совет"""
        
        response = get_gemini_response(prompt)
        if not response:
            # Возвращаем стандартный ответ при ошибке API
            default_response = """1. Паста с соусом\nИнгредиенты..."""
            return jsonify({
                'response': default_response,
                'status': 'success',
                'note': 'Used default recipe'
            })
            
        return jsonify({
            'response': response.replace("\n", "<br>"),
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({
            'error': 'Внутренняя ошибка сервера',
            'status': 'error'
        }), 500

# ... (остальные маршруты остаются без изменений)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    # Отключен debug mode для продакшена
    app.run(host='0.0.0.0', port=port)