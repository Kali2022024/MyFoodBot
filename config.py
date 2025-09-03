import os
from dotenv import load_dotenv

# Завантажуємо змінні середовища з .env файлу
load_dotenv()

# Конфігурація бота
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-haiku-20241022")

# Перевіряємо наявність обов'язкових змінних
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не знайдено в змінних середовища")

if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY не знайдено в змінних середовища")

print(f"✅ Конфігурація завантажена:")
print(f"   Модель Claude: {CLAUDE_MODEL}")
print(f"   Telegram Bot: {'✅' if TELEGRAM_BOT_TOKEN else '❌'}")
print(f"   Anthropic API: {'✅' if ANTHROPIC_API_KEY else '❌'}")
