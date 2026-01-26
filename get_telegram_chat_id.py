"""
Скрипт для получения Telegram Chat ID.

Использование:
1. Убедитесь, что TELEGRAM_BOT_TOKEN указан в .env
2. Напишите боту /start в Telegram
3. Запустите скрипт: python get_telegram_chat_id.py
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from telegram import Bot

# Загружаем .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Загружен .env из {env_path}")
else:
    print(f"⚠ .env файл не найден: {env_path}")

bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

if not bot_token:
    print("❌ Ошибка: TELEGRAM_BOT_TOKEN не найден в .env")
    print("\nДобавьте в .env файл:")
    print("TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather")
    exit(1)

print(f"✓ Токен найден (длина: {len(bot_token)} символов)")
print("\n" + "="*60)
print("Получение информации о боте и последних сообщениях...")
print("="*60 + "\n")

async def get_chat_id():
    """Получить chat_id из последних сообщений бота."""
    bot = Bot(token=bot_token)
    
    # Получаем информацию о боте
    try:
        bot_info = await bot.get_me()
        print(f"✓ Бот: @{bot_info.username} ({bot_info.first_name})")
        print()
    except Exception as e:
        print(f"❌ Ошибка при получении информации о боте: {e}")
        print("Проверьте правильность TELEGRAM_BOT_TOKEN")
        return
    
    # Получаем обновления (последние сообщения)
    try:
        updates = await bot.get_updates(limit=10)
        
        if not updates:
            print("⚠ Не найдено сообщений от пользователей")
            print("\nИнструкция:")
            print("1. Найдите вашего бота в Telegram: @{}".format(bot_info.username))
            print("2. Напишите боту /start")
            print("3. Запустите этот скрипт снова")
            return
        
        print(f"✓ Найдено {len(updates)} обновлений\n")
        print("="*60)
        print("Найденные чаты:")
        print("="*60)
        
        seen_chats = set()
        for update in updates:
            if update.message:
                chat = update.message.chat
                chat_id = chat.id
                
                if chat_id not in seen_chats:
                    seen_chats.add(chat_id)
                    
                    chat_type = chat.type
                    chat_name = chat.title or chat.first_name or chat.username or "N/A"
                    
                    print(f"\n📱 Тип: {chat_type}")
                    print(f"   Chat ID: {chat_id}")
                    print(f"   Имя: {chat_name}")
                    
                    if chat_type == "private":
                        print(f"   👤 Это ваш личный чат с ботом!")
                        print(f"\n   ✅ Добавьте в .env:")
                        print(f"   TELEGRAM_CHAT_ID={chat_id}")
                    elif chat_type == "group":
                        print(f"   👥 Это группа")
                    elif chat_type == "channel":
                        print(f"   📢 Это канал")
                        print(f"   ⚠ Для каналов бот должен быть администратором")
        
        if seen_chats:
            print("\n" + "="*60)
            print("💡 Совет:")
            print("   Для личных сообщений используйте Chat ID из 'private' чата")
            print("="*60)
        else:
            print("\n⚠ Не найдено чатов")
            print("\nИнструкция:")
            print("1. Найдите вашего бота в Telegram: @{}".format(bot_info.username))
            print("2. Напишите боту /start")
            print("3. Запустите этот скрипт снова")
            
    except Exception as e:
        print(f"❌ Ошибка при получении обновлений: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("="*60)
    print("  Получение Telegram Chat ID")
    print("="*60)
    print()
    
    try:
        asyncio.run(get_chat_id())
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
