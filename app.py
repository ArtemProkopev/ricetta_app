import os
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

GEMINI_API_KEY = "AIzaSyBx19-uNqyD5WaZB0mWJ7agoigG0hTGMtQ"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

def get_gemini_response(prompt):
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    response = requests.post(GEMINI_URL, json=data, headers=headers)
    if response.status_code == 200:
        try:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError):
            return None
    return None

@app.route('/')
def home():
    return send_from_directory('static', 'main.html')

@app.route('/ai')
def ai_page():
    return render_template('ai-search.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_input = request.json.get('message', '').strip()
        
        if not user_input:
            return jsonify({'error': 'Пожалуйста, введите ингредиенты'}), 400
            
        prompt = f"""Создай 2 рецепта используя: {user_input}. Формат для каждого:
        1. Название блюда
        2. Ингредиенты:
           - Есть: [список]
           - Купить: [список]
        3. Рецепт: пошагово
        4. Время приготовления
        5. Совет"""
        
        response = get_gemini_response(prompt)
        
        if not response:
            raise ValueError("Не удалось получить ответ от Gemini API")
            
        return jsonify({
            'response': response.replace("\n", "<br>"),
            'status': 'success'
        })

    except Exception as e:
        return jsonify({
            'error': f'Ошибка: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/categories/<category_name>.html')
def show_category(category_name):
    return send_from_directory(os.path.join(app.root_path, 'categories'), 
                             f'{category_name}.html')

@app.route('/recept/<int:recept_id>')
def show_recept(recept_id):
    return send_from_directory('codeofrecept', f'recept{recept_id}.html')

@app.route('/register')
def register_page():
    return send_from_directory('ricetta-project-end', 'register.html')

@app.route('/register/<path:filename>')
def register_static(filename):
    return send_from_directory('ricetta-project-end', filename)

@app.route('/login')
def login_page():
    return send_from_directory('ricetta-project-end', 'login.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)