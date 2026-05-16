import telebot
import requests
import json
import time
import os

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

def get_free_proxy():
    try:
        response = requests.get('https://api.proxyscrape.com/?request=getproxies&proxytype=http&timeout=10000&country=all&ssl=all&anonymity=all', timeout=10)
        proxies = response.text.split('\r\n')
        for proxy in proxies[:10]:
            if not proxy:
                continue
            test_url = "https://api.telegram.org"
            try:
                requests.get(test_url, proxies={'https': proxy}, timeout=5)
                return proxy
            except:
                continue
    except Exception as e:
        print(f"Ошибка при поиске прокси: {e}")
    return None

proxy = get_free_proxy()
if proxy:
    from telebot import apihelper
    apihelper.proxy = {'https': proxy}
    print(f"Используется прокси: {proxy}")
else:
    print("Прокси не найден, пробуем прямое соединение")

bot = telebot.TeleBot(BOT_TOKEN)

# Список актуальных бесплатных моделей на OpenRouter
AVAILABLE_FREE_MODELS = [
    "openrouter/openrouter/free", 
    "tencent/hy3-preview:free", 
    "openai/gpt-oss-120b:free",  
    "nvidia/nemotron-3-super-120b-a12b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free", 
    "google/gemma-4-31b-it:free", 
    "z-ai/glm-4.5-air:free", 
    "minimax/minimax-m2.5:free",
]
def ask_ai_with_retry(question, model_index=0):
    """Отправляет запрос к OpenRouter с автоматическим переключением между моделями"""
    if model_index >= len(AVAILABLE_FREE_MODELS):
        return "Все доступные модели временно недоступны. Пожалуйста, попробуйте позже."
    
    current_model = AVAILABLE_FREE_MODELS[model_index]
    
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://t.me/PolytechProjectBot",
            "X-Title": "Polytech Project Bot"
        }
        
        data = {
            "model": current_model,
            "messages": [
                {
                    "role": "user",
                    "content": question
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        if proxy:
            response = requests.post(url, headers=headers, json=data,
                                   proxies={'https': proxy}, timeout=60)
        else:
            response = requests.post(url, headers=headers, json=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            print(f"Модель {current_model} не работает (код {response.status_code}), пробуем следующую...")
            return ask_ai_with_retry(question, model_index + 1)
            
    except requests.exceptions.Timeout:
        return f"Превышено время ожидания от модели {current_model}. Пробую другую..."
    except Exception as e:
        print(f"Ошибка с моделью {current_model}: {e}")
        return ask_ai_with_retry(question, model_index + 1)

def ask_ai(question):
    """Отправляет запрос к OpenRouter с автоматическим переключением моделей"""
    return ask_ai_with_retry(question, 0)

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, 
        "Привет! Я бот с искусственным интеллектом!\n\n"
        "Используй команду /ai [вопрос]\n"
        "Пример: /ai Какой сегодня день?\n"
        "Пример: /ai Напиши код на Python для калькулятора\n\n"
        "Я использую современные бесплатные ИИ-модели\n"
        "Вопросы пиши на любом языке!"
    )

@bot.message_handler(commands=['ai'])
def handle_ai(message):
    # Получаем текст после команды /ai
    question = message.text.replace('/ai', '').strip()
    
    if not question:
        bot.reply_to(message, 
            "Пожалуйста, напиши вопрос после команды /ai\n\n"
            "Пример: /ai Как дела?\n"
            "Пример: /ai Что такое Python?"
        )
        return
    
    status_msg = bot.reply_to(message, f"Думаю над вашим вопросом...\nВопрос: {question[:100]}{'...' if len(question) > 100 else ''}")
    
    answer = ask_ai(question)
    
    if len(answer) > 4000:
        bot.edit_message_text("Ответ очень длинный, отправляю по частям...", 
                            message.chat.id, status_msg.message_id)
        for i in range(0, len(answer), 4000):
            bot.send_message(message.chat.id, answer[i:i+4000])
        bot.send_message(message.chat.id, "Ответ полностью отправлен!")
    else:
        bot.edit_message_text(answer, message.chat.id, status_msg.message_id)

@bot.message_handler(commands=['models'])
def show_models(message):
    """Показывает список доступных моделей"""
    models_list = "\n".join([f"• {model}" for model in AVAILABLE_FREE_MODELS])
    bot.reply_to(message,
        f"Доступные модели ИИ:\n\n{models_list}\n\n"
        f"Первая модель в списке используется по умолчанию\n"
        f"При ошибке бот автоматически переключается на следующую"
    )

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message,
        "Доступные команды:\n\n"
        "/start или /hello - Приветствие\n"
        "/ai [вопрос] - Задать вопрос искусственному интеллекту\n"
        "/models - Показать доступные модели ИИ\n"
        "/help - Показать эту справку\n\n"
        "Просто напишите /ai и ваш вопрос\n"
        "Если одна модель не работает, бот автоматически переключится на другую"
    )

@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    if not message.text.startswith('/'):
        bot.reply_to(message, 
            f"Я понял ваше сообщение, но я отвечаю только на команду /ai\n\n"
            f"Попробуйте: /ai {message.text[:50]}"
        )

print("Бот успешно запущен и готов к работе!")
print("Используйте команду /ai для общения с ИИ")
print("Доступные модели: " + ", ".join(AVAILABLE_FREE_MODELS[:3]) + "...")
bot.infinity_polling()
