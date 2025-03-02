import os
import requests
import json
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)

API_KEY = "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"
MODEL = "deepseek/deepseek-r1"

def process_content(content):
    return content.replace('<think>', '').replace('</think>', '')

def chat_stream(prompt):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True
    }

    with requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data,
        stream=True
    ) as response:
        if response.status_code != 200:
            print("Ошибка API:", response.status_code)
            return ""

        full_response = []
        
        for chunk in response.iter_lines():
            if chunk:
                chunk_str = chunk.decode('utf-8').replace('data: ', '')
                try:
                    chunk_json = json.loads(chunk_str)
                    if "choices" in chunk_json:
                        content = chunk_json["choices"][0]["delta"].get("content", "")
                        if content:
                            cleaned = process_content(content)
                            full_response.append(cleaned)
                except:
                    pass

        return ''.join(full_response)

@app.route('/')
def index():
    # Отдаём главную страницу (main.html) из папки static
    return send_from_directory('static', 'main.html')

@app.route('/ai')
def ai_page():
    # Отдаём страницу ИИ (ai-search.html) из папки templates
    return render_template('ai-search.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message')
    response = chat_stream(user_input)
    return jsonify({'response': response})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
