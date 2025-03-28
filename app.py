import os
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from markdownify import markdownify as md
import markdown
import re

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

GEMINI_API_KEY = "AIzaSyBry_e6sHvUPqTu0jmvR9uCa50s1tH6GtM"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

def get_gemini_response(prompt):
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(GEMINI_URL, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception:
        return None

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

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
        ---
        ### **Рецепт 1**
        #### **Название блюда**
        [название]
        
        #### **Ингредиенты**
        - Есть: [список]
        - Купить: [список]
        
        #### **Пошаговый рецепт**
        1. [шаг 1]
        2. [шаг 2]
        3. [шаг 3]
        
        #### **Время приготовления**
        [время]
        
        #### **Совет**
        *Совет по приготовлению*
        
        ---
        ### **Рецепт 2**
        #### **Название блюда**
        [название]
        
        #### **Ингредиенты**
        - Есть: [список]
        - Купить: [список]
        
        #### **Пошаговый рецепт**
        1. [шаг 1]
        2. [шаг 2]
        3. [шаг 3]
        
        #### **Время приготовления**
        [время]
        
        #### **Совет**
        *Совет по приготовлению*
        ---
        """
        
        response = get_gemini_response(prompt)
        if not response:
            raise ValueError("Не удалось получить ответ от Gemini API")
        
        cleaned_response = re.sub(r'\*\*', '', response) 
        cleaned_response = re.sub(r'__|\*\*|\*\*__', '', cleaned_response)
        
        markdown_response = md(cleaned_response.replace("\n", "<br>"))
        
        html_response = markdown.markdown(markdown_response)
        
        return jsonify({
            'response': html_response,
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
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)