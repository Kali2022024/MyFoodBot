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

LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Налаштування бази даних
DATABASE_PATH = "subscriptions.db"

# Налаштування очищення статистики (в годинах)
CLEANUP_INTERVAL_HOURS = 24

# Адміністратори (список Telegram ID)                                                  

# Налаштування підписок
SUBSCRIPTION_PRICE_USD = 0.01  # 🧪 ТЕСТОВА ЦІНА! (було 2)
FREE_TRIALS_COUNT = 2
SUBSCRIPTION_DURATION_DAYS = 30

# ===================================
# ПЛАТІЖНА СИСТЕМА
# ===================================

# Ціни підписки
SUBSCRIPTION_PRICE_STARS = 100  # Telegram Stars (еквівалент $2)
SUBSCRIPTION_PRICE_UAH = 80     # Українські гривні

# Telegram Stars (вбудована платіжна система)
# Налаштуйте в @BotFather → Payments → Telegram Stars
TELEGRAM_STARS_ENABLED = True

# CryptoBot (для криптовалют)
CRYPTOBOT_API_TOKEN = os.getenv("CRYPTOBOT_API_TOKEN", "")  # Додайте в .env
CRYPTOBOT_ENABLED = bool(CRYPTOBOT_API_TOKEN)

# Ваші криптогаманці (додайте ваші адреси)
USDT_TRC20_WALLET = os.getenv("USDT_TRC20_WALLET")  
BTC_WALLET = os.getenv("BTC_WALLET")
ETH_WALLET = os.getenv("ETH_WALLET")

# LiqPay (для українських карток Monobank/PrivatBank)
LIQPAY_PUBLIC_KEY = os.getenv("LIQPAY_PUBLIC_KEY", "")
LIQPAY_PRIVATE_KEY = os.getenv("LIQPAY_PRIVATE_KEY", "")
LIQPAY_ENABLED = bool(LIQPAY_PUBLIC_KEY and LIQPAY_PRIVATE_KEY)

# Ваша картка Monobank для ручної оплати
MONOBANK_CARD = "5168 XXXX XXXX XXXX"  # Додайте вашу картку

# Payment Provider для Apple Pay / Google Pay (Fondy, YooKassa, і т.д.)
# Отримайте Provider Token в @BotFather → Payments
PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN", "")  # Додайте в .env
PAYMENT_PROVIDER_ENABLED = bool(PAYMENT_PROVIDER_TOKEN)

# Простий USDT TRC20 гаманець для оплати
USDT_TRC20_WALLET = os.getenv("USDT_TRC20_WALLET", "")

print(f"💳 Платіжна система:")
print(f"   💰 USDT TRC20: {'✅ ' + USDT_TRC20_WALLET[:10] + '...' if USDT_TRC20_WALLET else '❌ (додайте в .env)'}")
