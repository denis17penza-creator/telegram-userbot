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

if not API_ID or not API_HASH or not GROQ_API_KEY:
    raise ValueError("Ошибка: не заданы API_ID, API_HASH или GROQ_API_KEY")

HISTORY_FILE = 'chat_histories.json'

SYSTEM_PROMPT = """Ты обычный человек. Ты общаешься с другом в Telegram. Твои правила:
- Отвечай как живой человек: используй сленг, иногда ошибки, короткие фразы
- Не будь слишком вежливым и официальным
- Пиши с маленькой буквы, без длинных предложений
- Отвечай по-русски
- Помни, о чём вы говорили ранее"""

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

async def get_chat_entity(user_id):
    """Получить сущность чата по user_id"""
    try:
        # Пробуем получить через диалоги
        async for dialog in client.iter_dialogs():
            if dialog.entity.id == user_id:
                return dialog.entity
        # Если не нашли, пробуем через get_entity
        return await client.get_entity(user_id)
    except Exception as e:
        print(f"⚠️ Ошибка получения сущности для {user_id}: {e}")
        return None

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
    
    # 🔥 НОВЫЙ МЕТОД: получаем сущность через диалоги
    chat_entity = await get_chat_entity(user_id)
    if not chat_entity:
        print(f"❌ Не удалось получить сущность для {user_id}")
        return
    
    try:
        # Отправляем статус "печатает"
        async with client.action(chat_entity, "typing"):
            await asyncio.sleep(random.uniform(1.5, 3.5))
            reply = await ask_groq_with_history(user_id, user_message)
            print(f"📤 [Ответ]: {reply}")
            await client.send_message(chat_entity, reply)
    except Exception as e:
        print(f"⚠️ Ошибка при отправке: {e}")

async def main():
    await client.start()
    
    # 🔥 ПРЕДВАРИТЕЛЬНАЯ ЗАГРУЗКА ДИАЛОГОВ
    print("🔄 Загрузка диалогов...")
    async for _ in client.iter_dialogs(limit=10):
        pass  # Просто проходим по диалогам, чтобы заполнить кэш
    print("✅ Диалоги загружены")
    
    print("\n" + "="*50)
    print("✅ Бот запущен (с предзагрузкой диалогов)")
    print("📌 Теперь напиши второму аккаунту с основного")
    print("="*50 + "\n")
    
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
