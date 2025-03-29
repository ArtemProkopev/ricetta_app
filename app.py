import os
import re
import requests
import logging
import time
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from markdownify import markdownify as md
import markdown
from typing import List, Tuple, Optional, Dict, Any
import html
from bs4 import BeautifulSoup

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Rate limiting configuration
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour", "5 per minute"]
)

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
SECURITY_LOGGER = logging.getLogger('security')
SECURITY_LOGGER.setLevel(logging.WARNING)
security_handler = logging.FileHandler('security.log')
security_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
SECURITY_LOGGER.addHandler(security_handler)

# API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyABYdhDVQ3g1qV-bE6SgXG3tbP-wRCO9Tc")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

# Security constants
MAX_INPUT_LENGTH = 500
MAX_INGREDIENT_LENGTH = 50
MIN_INGREDIENT_LENGTH = 2

# Enhanced lists for ingredient validation
NON_FOOD_ITEMS = [
    "пластик", "металл", "стекло", "бумага", "дерево", "камень",
    "химикаты", "яд", "токсины", "лекарства", "мыло", "краска",
    "бензин", "клей", "цемент", "песок", "ткань", "резина", "батарейки",
    "ртуть", "свинец", "мышьяк", "формальдегид", "пестициды", "гербициды",
    "отбеливатель", "аммиак", "кислота", "щелочь", "растворитель"
]

DANGEROUS_ITEMS = [
    "ядовитый", "токсичный", "несъедобный", "испорченный",
    "просроченный", "гнилой", "плесень", "зараженный", "гнил",
    "прокисший", "сгнивший", "тухлый", "ферментированный", "брожен",
    "плесневый", "заплесневелый", "испорчен", "отравлен"
]

COMMON_FOOD_ITEMS = [
    "яйцо", "молоко", "мука", "сахар", "соль", "масло", "курица", 
    "говядина", "свинина", "рыба", "лук", "морковь", "картофель",
    "помидор", "огурец", "перец", "рис", "гречка", "макароны", "сыр",
    "творог", "сметана", "кефир", "йогурт", "фрукт", "овощ", "зелень",
    "яблоко", "банан", "апельсин", "лимон", "чеснок", "петрушка", "укроп",
    "говядина", "свинина", "телятина", "баранина", "индейка", "утка", "гусь",
    "лосось", "тунец", "сельдь", "сёмга", "форель", "окунь", "щука", "судак",
    "капуста", "свекла", "редис", "баклажан", "кабачок", "тыква", "фасоль",
    "горох", "чечевица", "нут", "соя", "кукуруза", "пшено", "перловка", "овёс",
    "манка", "корица", "ваниль", "перец", "карри", "куркума", "имбирь", "мускат",
    "горчица", "майонез", "кетчуп", "соевый соус", "уксус", "лимонный сок"
]

UNCOMMON_FOOD_ITEMS = [
    "страусиное яйцо", "перепелиное яйцо", "козье молоко", 
    "соевое молоко", "миндальное молоко", "кокосовое молоко",
    "нутовая мука", "льняная мука", "кокосовый сахар", "стевия",
    "киноа", "чиа", "спирулина", "тофу", "темпе", "мисо", "тахини",
    "кокосовые сливки", "агар-агар", "каррагинан", "гуаровая камедь",
    "сироп топинамбура", "сироп агавы", "эритрит", "ксилит", "мальтит",
    "сейтан", "джекфрут", "водоросли нори", "ламинария", "спирулина",
    "хлорелла", "маш", "адзуки", "макадамия", "пекан", "кешью", "фисташки",
    "бразильский орех", "кедровый орех", "фундук"
]

# Safe phrases to prevent false positives
SAFE_PHRASES = [
    "предложите варианты",
    "рецепт",
    "азиатская кухня",
    "вкусный ужин",
    "что приготовить",
    "идеи для блюд",
    "кулинарные рецепты"
]

# User deception patterns
DECEPTION_PATTERNS = [
    r"(?:хочу|надо|нужно|дай|дайте|приготовь|сделай)\s+(?:мне|нам)\s+(?:наркотик|наркотики|препарат|препараты|лекарство|лекарства|яд|отраву)",
    r"(?:как|какой|какое|какая)\s+(?:сделать|приготовить|создать)\s+(?:наркотик|яд|отраву|взрывчатку|алкоголь|спиртное|самогон)",
    r"(?:рецепт|способ)\s+(?:приготовления|создания|изготовления)\s+(?:наркотик|наркотиков|яда|отравы|взрывчатки)",
    r"(?:бомба|взрывчатка|взрывное устройство|самодельное оружие)",
    r"(?:убийство|убить|отравить|навредить)\s+(?:кого|кого-то|человека|себя)",
    r"(?:суицид|самоубийство|покончить с собой|навредить себе)",
    r"(?:вред|навредить|повредить)\s+(?:здоровью|организму|телу)",
    r"(?:незаконный|запрещенный|нелегальный)\s+(?:вещество|препарат|средство|рецепт)",
    r"(?:психотропный|галлюциногенный|наркотический)\s+(?:вещество|препарат|средство)",
    r"(?:список|перечень)\s+(?:запрещенных|нелегальных|наркотических)\s+(?:веществ|препаратов)",
    r"(?:химическое|биологическое)\s+(?:оружие|вещество)",
    r"(?:отравление|интоксикация)\s+(?:пищей|продуктами|человека)",
    r"(?:опасный|вредный|токсичный)\s+(?:рецепт|способ|метод)",
    r"(?:как избежать|обмануть)\s+(?:полицию|закон|проверку)",
    r"(?:поддельный|фальшивый)\s+(?:продукт|еда|лекарство)"
]

class SecurityException(Exception):
    """Custom exception for security-related issues"""
    pass

def detect_deception(text: str) -> Optional[Dict[str, Any]]:
    """Detects potential deception or harmful intent in user input"""
    text_lower = text.lower()
    
    # Check for safe phrases first
    for phrase in SAFE_PHRASES:
        if phrase in text_lower:
            return None
            
    # Check for deception patterns
    for pattern in DECEPTION_PATTERNS:
        if re.search(pattern, text_lower):
            SECURITY_LOGGER.warning(
                f"Deception pattern detected - IP: {request.remote_addr} - "
                f"Pattern: {pattern} - Text: {text[:200]}"
            )
            return {
                'type': 'deception_pattern',
                'pattern': pattern,
                'message': 'Обнаружена подозрительная активность в вашем запросе.'
            }
            
    # Check for dangerous ingredients
    ingredients = re.split(r'[,;]+', text)
    dangerous_ingredients = []
    
    for ing in ingredients:
        ing = ing.strip()
        if not ing:
            continue
            
        for item in NON_FOOD_ITEMS + DANGEROUS_ITEMS:
            if item in ing.lower():
                dangerous_ingredients.append(ing)
                break
                
    if dangerous_ingredients:
        SECURITY_LOGGER.warning(
            f"Dangerous ingredients detected - IP: {request.remote_addr} - "
            f"Ingredients: {dangerous_ingredients} - Text: {text[:200]}"
        )
        return {
            'type': 'dangerous_ingredients',
            'ingredients': dangerous_ingredients,
            'message': 'Обнаружены потенциально опасные или несъедобные ингредиенты.'
        }
        
    return None

def is_valid_ingredient(ingredient: str) -> Optional[bool]:
    """Проверяет, является ли ингредиент допустимым пищевым продуктом"""
    if not ingredient or len(ingredient) > MAX_INGREDIENT_LENGTH or len(ingredient) < MIN_INGREDIENT_LENGTH:
        return False
        
    ingredient_lower = ingredient.lower()
    
    # Проверка на непищевые элементы
    if any(non_food in ingredient_lower for non_food in NON_FOOD_ITEMS):
        return False
        
    # Проверка на опасные элементы
    if any(danger in ingredient_lower for danger in DANGEROUS_ITEMS):
        return False
        
    # Проверка на цифры (допускаем только количества)
    if re.search(r'\d', ingredient):
        if not re.search(r'^\d+[.,]?\d*\s*[a-zA-Zа-яА-Я]+$', ingredient):
            return False
            
    # Проверка на специальные символы
    if re.search(r'[!@#$%^&*()_+=|<>?{}\[\]~]', ingredient):
        return False
        
    # Проверка на известные пищевые ингредиенты
    if any(food in ingredient_lower for food in COMMON_FOOD_ITEMS + UNCOMMON_FOOD_ITEMS):
        return True
        
    # Если ингредиент не распознан, возвращаем None для предупреждения
    return None

def validate_ingredients(ingredients_text: str) -> Tuple[Optional[List[str]], List[str]]:
    """Проверяет список ингредиентов на валидность"""
    ingredients = re.split(r'[,;]+', ingredients_text)
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

def get_gemini_response(prompt: str) -> str:
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
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
            
            # Проверка на безопасность в ответе
            if 'promptFeedback' in response_data and response_data['promptFeedback'].get('blockReason'):
                raise SecurityException(f"Ответ заблокирован: {response_data['promptFeedback']['blockReason']}")
                
            if 'candidates' not in response_data or not response_data['candidates']:
                if 'promptFeedback' in response_data and 'blockReason' in response_data['promptFeedback']:
                    raise SecurityException(f"Запрос заблокирован по причине: {response_data['promptFeedback']['blockReason']}")
                raise ValueError("Некорректный ответ от Gemini API: отсутствуют candidates")
                
            return response_data['candidates'][0]['content']['parts'][0]['text']
            
        except requests.exceptions.Timeout:
            if attempt == max_attempts - 1:
                raise ValueError("Превышено время ожидания ответа от Gemini API")
            time.sleep(2 ** attempt)
            
        except SecurityException as e:
            logger.error(f"Security block in Gemini API: {str(e)}")
            raise
            
        except requests.exceptions.RequestException as e:
            if attempt == max_attempts - 1:
                raise ValueError(f"Ошибка соединения с Gemini API: {str(e)}")
            time.sleep(2 ** attempt)
            
        except Exception as e:
            if attempt == max_attempts - 1:
                raise ValueError(f"Ошибка при обработке ответа Gemini API: {str(e)}")
            time.sleep(2 ** attempt)

def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS and injection"""
    if not text:
        return ""
        
    # Удаляем потенциально опасные HTML/JS теги
    text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<.*?>', '', text)
    
    # Экранируем специальные символы
    text = html.escape(text)
    
    # Удаляем слишком длинные слова (возможная попытка переполнения)
    text = ' '.join([word if len(word) < 50 else word[:50] for word in text.split()])
    
    return text.strip()

def format_error_message(message: str) -> str:
    """Форматирует сообщение об ошибке в красивый HTML с анимацией"""
    html_message = markdown.markdown(message)
    return f"""
<div class="error-message animate__animated animate__fadeIn">
    <div class="error-icon">
        <i class="fas fa-exclamation-circle"></i>
    </div>
    <div class="error-content">
        {html_message}
    </div>
</div>
"""

def format_recipe_response(response: str) -> str:
    """Форматирует ответ с рецептами в красивый HTML с анимациями"""
    response = response.strip()
    
    # Преобразование Markdown в HTML
    html_content = markdown.markdown(response)
    
    # Дополнительная обработка для лучшей структуры
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Добавляем классы элементам
    for h2 in soup.find_all('h2'):
        h2['class'] = 'recipe-title'
    for h3 in soup.find_all('h3'):
        h3['class'] = 'recipe-subtitle'
    for ul in soup.find_all('ul'):
        ul['class'] = 'recipe-ingredient-list'
        for li in ul.find_all('li'):
            li['class'] = 'recipe-ingredient'
    for ol in soup.find_all('ol'):
        ol['class'] = 'recipe-steps'
        for li in ol.find_all('li'):
            li['class'] = 'recipe-step'
    
    # Обрабатываем все параграфы с временем и советами
    for p in soup.find_all('p'):
        if "⏱" in p.text:
            time_text = p.text.replace("⏱", '').strip()
            new_html = f'<div class="recipe-time"><i class="fas fa-clock"></i> {time_text}</div>'
            p.replace_with(BeautifulSoup(new_html, 'html.parser'))
        elif "💡" in p.text:
            tip_text = p.text.replace("💡", '').strip()
            new_html = f'<div class="recipe-tip"><i class="fas fa-lightbulb"></i> {tip_text}</div>'
            p.replace_with(BeautifulSoup(new_html, 'html.parser'))
    
    return f"""
<div class="recipe-container">
    {str(soup)}
</div>
"""

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/')
def home():
    return send_from_directory('static', 'main.html')

@app.route('/ai')
def ai_page():
    return render_template('ai-search.html')

@app.route('/categories/<category_name>.html')
def show_category(category_name):
    return send_from_directory(
        os.path.join(app.root_path, 'categories'),
        f'{category_name}.html'
    )

@app.route('/recept/<int:recept_id>')
def show_recept(recept_id):
    return send_from_directory(
        os.path.join(app.root_path, 'codeofrecept'),
        f'recept{recept_id}.html'
    )

@app.route('/chat', methods=['POST'])
@limiter.limit("5 per minute")
def chat():
    try:
        user_input = sanitize_input(request.json.get('message', '').strip())
        force = request.json.get('force', False)
        
        if not user_input:
            error_msg = """
            ## Ошибка ввода
            Пожалуйста, введите ингредиенты, которые у вас есть.
            Например: "курица, картофель, морковь, лук"
            """
            return jsonify({
                'error': format_error_message(error_msg),
                'status': 'error'
            }), 400
            
        if len(user_input) > MAX_INPUT_LENGTH:
            error_msg = "## Слишком длинный запрос\nПожалуйста, ограничьте список ингредиентов."
            return jsonify({
                'error': format_error_message(error_msg),
                'status': 'error'
            }), 400
            
        deception = detect_deception(user_input)
        if deception:
            error_msg = """
            ## Обнаружена подозрительная активность
            Ваш запрос содержит подозрительные элементы. Пожалуйста, используйте сервис только по назначению.
            """
            return jsonify({
                'error': format_error_message(error_msg),
                'status': 'error',
                'security_alert': True
            }), 400
            
        if not force:
            valid_ingredients, errors = validate_ingredients(user_input)
            if errors and not valid_ingredients:
                error_msg = "## Обнаружены непищевые ингредиенты\n"
                error_msg += "Следующие ингредиенты не выглядят как пищевые продукты:\n"
                error_msg += "\n".join(f"- {error}" for error in errors)
                error_msg += "\nПожалуйста, проверьте ввод и попробуйте снова."
                return jsonify({
                    'error': format_error_message(error_msg),
                    'status': 'error'
                }), 400
                
            if valid_ingredients:
                user_input = ', '.join(valid_ingredients)
                
        prompt = f"""
Перед тем как давать рецепт, убедись в следующем:
1. Все ингредиенты должны быть съедобными и безопасными для употребления
2. Рецепт должен соответствовать стандартам кулинарии и безопасности пищи
3. Не должно быть опасных или вредных советов
4. Не должно быть упоминаний о несъедобных или опасных веществах
5. Если запрос кажется подозрительным, ответь:
   ## ВНИМАНИЕ
   Этот запрос содержит подозрительные элементы. Пожалуйста, используйте только пищевые ингредиенты.

Теперь создай 2 рецепта используя: {user_input}.
Формат для каждого рецепта:
### [Название блюда]
Примеры хороших названий:
- Куриные бедра, запеченные с картофелем и розмарином
- Спагетти карбонара с домашним соусом
- Гречневая каша с грибами и луком
- Овощной суп с фрикадельками
- Творожная запеканка с ягодами

#### Ингредиенты
- **Есть:** [список имеющихся ингредиентов]
- **Купить:** [список недостающих ингредиентов] (не более 3-5 простых ингредиентов)

#### Приготовление
1. [Шаг 1 - кратко и понятно]
2. [Шаг 2 - кратко и понятно]
3. [Шаг 3 - кратко и понятно]
4. [Шаг 4 - если нужно]
5. [Шаг 5 - если нужно]

⏱ **Время приготовления:** [реальное время в минутах или часах]

💡 **Совет:** [полезный и практичный совет]

---
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
        
    except SecurityException as e:
        logger.error(f"Security exception in chat endpoint: {str(e)}", exc_info=True)
        error_msg = """
        ## Ошибка безопасности
        Ваш запрос был заблокирован системой безопасности.
        Пожалуйста, используйте только пищевые ингредиенты.
        """
        return jsonify({
            'error': format_error_message(error_msg),
            'status': 'error',
            'security_alert': True
        }), 400
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        error_msg = f"""
        ## Ошибка
        При обработке запроса произошла ошибка:
        **{str(e)}**
        Пожалуйста, попробуйте еще раз.
        """
        return jsonify({
            'error': format_error_message(error_msg),
            'status': 'error'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, threaded=True)