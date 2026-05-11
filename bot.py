import asyncio
import random
import json
import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from groq import Groq

# ========== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ==========
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
SESSION_STRING = os.getenv('SESSION_STRING', '')

# 🔥 ТВОЙ USER_ID (узнай через @userinfobot)
MY_USER_ID = 1101377117  # ЗАМЕНИ НА СВОИ ЦИФРЫ!

if not API_ID or not API_HASH or not GROQ_API_KEY:
    raise ValueError("Ошибка: не заданы API_ID, API_HASH или GROQ_API_KEY")

HISTORY_FILE = 'chat_histories.json'

SYSTEM_PROMPT = """Тебя зовут Настя. Ты девушка. Ты общаешься со своим парнем в Telegram. Твои правила:
- Отвечай естественно, короткими фразами
- Не используй обращения вроде «зайка», «друг», «братан» и т.п.
- Пиши с маленькой буквы
- Иногда используй эмодзи, но не перебарщивай
- Будь спокойным и нейтральным
- Не обижайся, не радуйся слишком сильно, не драматизируй
- Если не знаешь ответа — напиши «хз» или «не знаю»
- Отвечай по-русски"""

# Инициализация клиента
if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    client = TelegramClient('userbot_session', API_ID, API_HASH)

groq_client = Groq(api_key=GROQ_API_KEY)

def load_histories():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_histories(histories):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(histories, f, ensure_ascii=False, indent=2)

async def ask_groq_with_history(user_id, new_message):
    histories = load_histories()
    user_id_str = str(user_id)
    if user_id_str not in histories:
        histories[user_id_str] = []
    
    history = histories[user_id_str][-10:]
    
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
        
        histories[user_id_str].append({"role": "user", "content": new_message})
        histories[user_id_str].append({"role": "assistant", "content": reply})
        if len(histories[user_id_str]) > 30:
            histories[user_id_str] = histories[user_id_str][-30:]
        save_histories(histories)
        
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
    
    # 📌 ОТВЕЧАЕМ ТОЛЬКО ТЕБЕ (по user_id)
    if user_id != MY_USER_ID:
        print(f"📥 [Игнорирую {user_id}]: не владелец")
        return
    
    print(f"\n📥 [От {user_id}]: {user_message}")
    
    # Просто засыпаем и отвечаем через send_message
    await asyncio.sleep(random.uniform(1.5, 3.5))
    reply = await ask_groq_with_history(user_id, user_message)
    print(f"📤 [Ответ]: {reply}")
    await event.reply(reply)

async def main():
    await client.start()
    print("\n" + "="*50)
    print("✅ Бот запущен (отвечает только владельцу)")
    print(f"📌 Владелец: {MY_USER_ID}")
    print("📌 Напиши второму аккаунту с основного")
    print("="*50 + "\n")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
