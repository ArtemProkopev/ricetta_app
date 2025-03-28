import os
import re
import requests
import logging
import time
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from markdownify import markdownify as md
import markdown

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBry_e6sHvUPqTu0jmvR9uCa50s1tH6GtM")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

# Списки для валидации ингредиентов
NON_FOOD_ITEMS = [
    "пластик", "металл", "стекло", "бумага", "дерево", "камень",
    "химикаты", "яд", "токсины", "лекарства", "мыло", "краска",
    "бензин", "клей", "цемент", "песок", "ткань", "резина"
]

DANGEROUS_ITEMS = [
    "ядовитый", "токсичный", "несъедобный", "испорченный",
    "просроченный", "гнилой", "плесень", "зараженный"
]

COMMON_FOOD_ITEMS = [
    "яйцо", "молоко", "мука", "сахар", "соль", "масло", "курица", 
    "говядина", "свинина", "рыба", "лук", "морковь", "картофель",
    "помидор", "огурец", "перец", "рис", "гречка", "макароны", "сыр",
    "творог", "сметана", "кефир", "йогурт", "фрукт", "овощ", "зелень"
]

UNCOMMON_FOOD_ITEMS = [
    "страусиное яйцо", "перепелиное яйцо", "козье молоко", 
    "соевое молоко", "миндальное молоко", "кокосовое молоко",
    "нутовая мука", "льняная мука", "кокосовый сахар", "стевия"
]

def is_valid_ingredient(ingredient):
    """Проверяет, является ли ингредиент допустимым пищевым продуктом"""
    ingredient_lower = ingredient.lower()
    
    if any(non_food in ingredient_lower for non_food in NON_FOOD_ITEMS):
        return False
    
    if any(danger in ingredient_lower for danger in DANGEROUS_ITEMS):
        return False
    
    if len(ingredient) < 2 or len(ingredient) > 50:
        return False
    
    if re.search(r'\d', ingredient) and not re.search(r'^\d+[.,]?\d*\s*[a-zA-Zа-яА-Я]+$', ingredient):
        return False
    
    if any(food in ingredient_lower for food in COMMON_FOOD_ITEMS + UNCOMMON_FOOD_ITEMS):
        return True
    
    return None

def validate_ingredients(ingredients_text):
    """Проверяет список ингредиентов на валидность"""
    ingredients = re.split(r'[,;\n]+', ingredients_text)
    ingredients = [ing.strip() for ing in ingredients if ing.strip()]
    
    errors = []
    warnings = []
    valid_ingredients = []
    
    for ing in ingredients:
        validation_result = is_valid_ingredient(ing)
        
        if validation_result is False:
            errors.append(f"'{ing}' не похож на пищевой ингредиент")
        elif validation_result is None:
            warnings.append(f"'{ing}' - не уверен, что это съедобно. Проверьте правильность написания.")
            valid_ingredients.append(ing)
        else:
            valid_ingredients.append(ing)
    
    if not valid_ingredients and errors:
        return None, errors
    
    return valid_ingredients, warnings + errors

def get_gemini_response(prompt):
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_ONLY_HIGH"
            }
        ],
        "generationConfig": {
            "temperature": 0.9,
            "topP": 1,
            "topK": 1,
            "maxOutputTokens": 2048
        }
    }
    
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            response = requests.post(GEMINI_URL, json=data, headers=headers, timeout=30)
            
            if response.status_code != 200:
                error_msg = f"Gemini API error: {response.status_code}"
                if response.text:
                    try:
                        error_data = response.json()
                        error_msg += f" - {error_data.get('error', {}).get('message', 'Unknown error')}"
                    except:
                        error_msg += f" - {response.text[:200]}"
                raise ValueError(error_msg)
            
            response_data = response.json()
            
            if 'candidates' not in response_data or not response_data['candidates']:
                if 'promptFeedback' in response_data and 'blockReason' in response_data['promptFeedback']:
                    raise ValueError(f"Запрос заблокирован по причине: {response_data['promptFeedback']['blockReason']}")
                raise ValueError("Некорректный ответ от Gemini API: отсутствуют candidates")
            
            return response_data['candidates'][0]['content']['parts'][0]['text']
            
        except requests.exceptions.Timeout:
            if attempt == max_attempts - 1:
                raise ValueError("Превышено время ожидания ответа от Gemini API")
            time.sleep(2 ** attempt)
        except requests.exceptions.RequestException as e:
            if attempt == max_attempts - 1:
                raise ValueError(f"Ошибка соединения с Gemini API: {str(e)}")
            time.sleep(2 ** attempt)
        except Exception as e:
            if attempt == max_attempts - 1:
                raise ValueError(f"Ошибка при обработке ответа Gemini API: {str(e)}")
            time.sleep(2 ** attempt)

def format_error_message(message):
    """Форматирует сообщение об ошибке в красивый Markdown"""
    if "WARNING:" in message:
        message = message.replace("WARNING:", "## ⚠️ ВНИМАНИЕ")
    
    markdown_msg = f"""
<div class="error-message">
{markdown.markdown(message)}
</div>
"""
    return markdown_msg

def format_recipe_response(response):
    """Форматирует ответ с рецептами в красивый HTML"""
    # Улучшаем Markdown перед конвертацией
    response = re.sub(r'__(.+?)__', r'**\1**', response)  # Заменяем __ на **
    response = re.sub(r'^\*', '-', response, flags=re.MULTILINE)  # Заменяем * на - для списков
    
    html = markdown.markdown(response)
    
    # Добавляем CSS классы
    html = html.replace('<ul>', '<ul class="recipe-list">')
    html = html.replace('<ol>', '<ol class="recipe-steps">')
    html = html.replace('<h3>', '<h3 class="recipe-subheader">')
    html = html.replace('<h2>', '<h2 class="recipe-header">')
    
    return f'<div class="recipe-container">{html}</div>'

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
        force = request.json.get('force', False)
        
        if not user_input:
            error_msg = """
            ## ⚠️ Ошибка ввода
            
            Пожалуйста, введите ингредиенты, которые у вас есть.
            Например: "курица, картофель, морковь, лук"
            """
            return jsonify({
                'error': format_error_message(error_msg),
                'status': 'error'
            }), 400
        
        if not force:
            valid_ingredients, errors = validate_ingredients(user_input)
            
            if errors and not valid_ingredients:
                error_msg = "## ⚠️ Обнаружены непищевые ингредиенты\n\n"
                error_msg += "Следующие ингредиенты не выглядят как пищевые продукты:\n\n"
                error_msg += "\n".join(f"- {error}" for error in errors)
                error_msg += "\n\nПожалуйста, проверьте ввод и попробуйте снова."
                
                return jsonify({
                    'error': format_error_message(error_msg),
                    'status': 'error'
                }), 400
            
            if valid_ingredients:
                user_input = ', '.join(valid_ingredients)
        
        prompt = f"""
Создай 2 рецепта используя: {user_input}. 

Формат для каждого рецепта:

### Название блюда
[Креативное название]

#### Ингредиенты
- **Есть:** [список имеющихся ингредиентов]
- **Купить:** [список недостающих ингредиентов]

#### Приготовление
1. [Шаг 1]
2. [Шаг 2]
3. [Шаг 3]

⏱ **Время приготовления:** [время]

💡 **Совет:** [полезный совет]

---

Перед тем как давать рецепт, убедись, что все ингредиенты съедобны и безопасны. 
Если есть что-то подозрительное, ответь:

## ⚠️ ВНИМАНИЕ
Обнаружены потенциально опасные или несъедобные ингредиенты:
- [список ингредиентов]

Пожалуйста, используйте только пищевые продукты.
"""
        
        response = get_gemini_response(prompt)
        if not response:
            raise ValueError("Не удалось получить ответ от Gemini API")
        
        if "ВНИМАНИЕ:" in response or "WARNING:" in response:
            return jsonify({
                'error': format_error_message(response),
                'status': 'error'
            }), 400
        
        return jsonify({
            'response': format_recipe_response(response),
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        error_msg = f"""
        ## ⚠️ Ошибка
        
        При обработке запроса произошла ошибка:
        
        **{str(e)}**
        
        Пожалуйста, попробуйте еще раз.
        """
        return jsonify({
            'error': format_error_message(error_msg),
            'status': 'error'
        }), 500

# ... (остальные маршруты остаются без изменений)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)