import asyncio
import random
import json
import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from groq import Groq

# ========== ЧТЕНИЕ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ==========
# Эти значения будут подставлены из настроек Render (или из .env файла)
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
SESSION_STRING = os.getenv('SESSION_STRING', '')  # Необязательно, но упрощает деплой

# Проверка, что все переменные заданы
if not API_ID or not API_HASH or not GROQ_API_KEY:
    raise ValueError("Ошибка: не заданы API_ID, API_HASH или GROQ_API_KEY в переменных окружения")

# Файл для хранения истории диалогов (на сервере будет создаваться автоматически)
HISTORY_FILE = 'chat_histories.json'

SYSTEM_PROMPT = """Ты обычный человек. Ты общаешься с другом в Telegram. Твои правила:
- Отвечай как живой человек: используй сленг, иногда ошибки, короткие фразы
- Не будь слишком вежливым и официальным
- Пиши с маленькой буквы, без длинных предложений
- Иногда используй эмодзи, но не перебарщивай
- Отвечай по-русски
- Помни, о чём вы говорили ранее, обращайся к истории диалога"""

# Инициализация клиента Telegram
if SESSION_STRING:
    # Если есть сохранённая сессия — используем её (не надо вводить код при каждом запуске)
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    # Иначе создаём новую сессию (при первом запуске попросит номер и код)
    client = TelegramClient('userbot_session', API_ID, API_HASH)

groq_client = Groq(api_key=GROQ_API_KEY)

# Загрузка истории из файла
def load_histories():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# Сохранение истории в файл
def save_histories(histories):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(histories, f, ensure_ascii=False, indent=2)

# Получение истории пользователя (последние N сообщений)
def get_user_history(histories, user_id, limit=10):
    user_id_str = str(user_id)
    if user_id_str not in histories:
        histories[user_id_str] = []
    return histories[user_id_str][-limit:]

# Добавление сообщения в историю
def add_to_history(histories, user_id, role, content):
    user_id_str = str(user_id)
    if user_id_str not in histories:
        histories[user_id_str] = []
    histories[user_id_str].append({"role": role, "content": content})
    if len(histories[user_id_str]) > 30:
        histories[user_id_str] = histories[user_id_str][-30:]
    save_histories(histories)

async def ask_groq_with_history(user_id, new_message):
    histories = load_histories()
    history = get_user_history(histories, user_id, limit=10)
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": new_message})
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.9,
            max_tokens=150,
        )
        reply = response.choices[0].message.content.strip()
        
        add_to_history(histories, user_id, "user", new_message)
        add_to_history(histories, user_id, "assistant", reply)
        
        return reply
    except Exception as e:
        return f"🧠 ошибка: {str(e)[:50]}..."

@client.on(events.NewMessage(incoming=True))
async def handler(event):
    if not event.is_private:
        return
    
    if event.out:
        return
    
    user_message = event.text
    if not user_message:
        return
    
    user_id = event.sender_id
    print(f"\n📥 [От {user_id}]: {user_message}")
    
    async with client.action(event.chat_id, "typing"):
        await asyncio.sleep(random.uniform(1.5, 3.5))
        reply = await ask_groq_with_history(user_id, user_message)
        print(f"📤 [Ответ]: {reply}")
        await event.reply(reply)

async def main():
    await client.start()
    print("\n" + "="*50)
    print("✅ Бот запущен (с памятью, защитой от спама и без секретов в коде)")
    print("📌 Теперь напиши второму аккаунту с основного")
    print("="*50 + "\n")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
