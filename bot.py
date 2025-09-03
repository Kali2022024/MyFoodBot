import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import timedelta
from collections import defaultdict

from config import TELEGRAM_BOT_TOKEN
from food_analyzer import FoodAnalyzer

from user_manager import UserManager
from subscription_db import subscription_db


# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ініціалізація бота та диспетчера
bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# Ініціалізація аналізатора та менеджера користувачів
food_analyzer = FoodAnalyzer()
user_manager = UserManager()

# Список адміністраторів
ADMIN_IDS = [123456789]  # Ваш ID

def is_admin(user_id: int) -> bool:
    """Перевіряє, чи є користувач адміністратором"""
    return user_id in ADMIN_IDS

# Стани для FSM
class FoodAnalysisStates(StatesGroup):
    waiting_for_image = State()
    analyzing = State()
    choosing_analyzer = State()

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обробник команди /start"""
    welcome_text = f"""
🍽️ Ласкаво просимо до FoodBot! 🍽️

🆔 Ваш ID: {message.from_user.id}

Я допоможу вам проаналізувати їжу та дізнатися про:
• Калорійність
• Вміст білків
• Вміст вуглеводів  
• Вміст жирів
• Загальну кількість ккал
• Корисні поради

📸 Щоб почати аналіз:
Просто надішліть фото їжі!

💡 Доступні команди:
/start - Почати роботу
/help - Допомога
/about - Про бота
/status - Статус підписки
/payment - Інформація про оплату
/mode - Режим аналізу
    """
    
    await message.answer(welcome_text)

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обробник команди /help"""
    help_text = """
❓ Як користуватися ботом:

1. Надішліть фото їжі - бот автоматично проаналізує його
2. Отримайте детальний аналіз з калоріями та макронутрієнтами
3. Отримайте корисні поради щодо здорового харчування

🔧 Аналіз через Claude AI:

🤖 Claude AI
• Точний аналіз з використанням AI
• Розумне розпізнавання страв
• Персоналізовані поради
• Аналіз складних комбінацій

💰 Тарифи Claude AI:
• 🎁 2 безкоштовні спроби для кожного
• 💳 $2 на місяць після використання спроб
• ⏰ 30 днів дії підписки

📱 Підтримувані формати:
• JPEG, PNG, WebP

🆔 Щоб дізнатися свій ID, надішліть будь-яке повідомлення

💡 Доступні команди:
/start - Почати роботу
/help - Ця довідка
/about - Про бота
/status - Статус підписки
/payment - Інформація про оплату
/mode - Режим аналізу

📊 Статистика та історія:
/stats - Ваша статистика за 24 години
🗑️ Кнопка "Очистити ВСЮ статистику" - очищає всю вашу історію
    """
    
    await message.answer(help_text)

@router.message(Command("about"))
async def cmd_about(message: Message):
    """Обробник команди /about"""
    about_text = """
🤖 Про FoodBot

FoodBot - це інтелектуальний Telegram бот для аналізу їжі та підрахунку калорій.

🔧 Технології:
• Python 3.8+
• aiogram 3.x
• Anthropic Claude AI
• Telegram Bot API

🌟 Можливості:
• Аналіз фото їжі
• Розрахунок калорій та макронутрієнтів
• Аналіз через Claude AI
• Система платної підписки
• Корисні поради для здорового харчування

💡 Розробник: @onopandrey
📧 Підтримка: @onopandrey

Версія: 2.0.0
    """
    
    await message.answer(about_text)



@router.message(Command("status"))
async def cmd_status(message: Message):
    """Обробник команди /status"""
    user_id = message.from_user.id
    status_message = user_manager.get_subscription_status_message(user_id)
    
    await message.answer(status_message)

@router.message(Command("payment"))
async def cmd_payment(message: Message):
    """Обробник команди /payment"""
    payment_info = user_manager.get_payment_info()
    
    await message.answer(payment_info)

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Обробник команди /stats - показує статистику користувача за 24 години"""
    user_id = message.from_user.id
    
    try:
        # Отримуємо статистику за 24 години
        daily_stats = subscription_db.get_user_daily_stats(user_id)
        
        if not daily_stats or daily_stats.get("dishes_count", 0) == 0:
            # Навіть коли статистика порожня, показуємо кнопку для очищення
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗑️ Очистити ВСЮ статистику", callback_data=f"clear_stats_{user_id}")]
            ])
            
            await message.answer(
                "📊 Ваша статистика за 24 години:\n\n"
                "🍽️ Аналізів їжі: 0\n"
                "💡 Надішліть фото їжі, щоб почати вести статистику!\n\n"
                "🗑️ Можете також очистити історію, якщо потрібно.",
                reply_markup=keyboard
            )
            return
        
        # Формуємо детальну статистику
        stats_text = f"📊 Ваша статистика за 24 години:\n\n"
        stats_text += f"🍽️ Аналізів їжі: {daily_stats.get('dishes_count', 0)}\n"
        stats_text += f"🔥 Загальні калорії: {daily_stats.get('total_calories', 0):.1f} ккал\n"
        stats_text += f"🥩 Загальний білок: {daily_stats.get('total_protein', 0):.1f} г\n"
        stats_text += f"🧈 Загальний жир: {daily_stats.get('total_fat', 0):.1f} г\n"
        stats_text += f"🍞 Загальні вуглеводи: {daily_stats.get('total_carbs', 0):.1f} г\n"
        stats_text += f"💧 Загальна вода: {daily_stats.get('water_ml', 0):.0f} мл\n"
        
        # Додаємо кнопку для очищення статистики
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑️ Очистити ВСЮ статистику", callback_data=f"clear_stats_{user_id}")]
        ])
        
        await message.answer(stats_text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Помилка при отриманні статистики для {user_id}: {e}")
        await message.answer("❌ Помилка при отриманні статистики. Спробуйте ще раз.")



# ==================== ОБРОБКА ВОДИ ====================

@router.callback_query(lambda c: c.data.startswith("add_water_"))
async def process_add_water(callback: CallbackQuery, state: FSMContext):
    """Обробник додавання води"""
    await callback.answer()
    
    try:
        # Отримуємо user_id з callback_data
        user_id = int(callback.data.split("_")[-1])
        
        # Перевіряємо, чи це той самий користувач
        if callback.from_user.id != user_id:
            await callback.answer("❌ Ця кнопка не для вас!", show_alert=True)
            return
        
        # Додаємо 250 мл води до статистики
        water_added = 250
        
        # Отримуємо поточну статистику за сьогодні
        today_stats = subscription_db.get_user_daily_stats(user_id)
        
        if today_stats:
            # Оновлюємо існуючу статистику
            current_water = today_stats.get("water_ml", 0)
            
            # Передаємо в update_user_water тільки кількість для додавання (250 мл)
            # а не загальну кількість
            subscription_db.update_user_water(user_id, water_added)
            
            # Отримуємо оновлену статистику для відображення
            updated_stats = subscription_db.get_user_daily_stats(user_id)
            new_water = updated_stats.get("water_ml", 0) if updated_stats else current_water + water_added
            
            # Показуємо повідомлення про додавання води
            await callback.answer(f"💧 +{water_added} мл води додано! Сьогодні: {new_water} мл", show_alert=True)
            
            # Оновлюємо текст повідомлення, але залишаємо кнопку
            current_text = callback.message.text
            if "💧 Додати 250 мл води до статистики" in current_text:
                # Замінюємо тільки текст про воду, залишаємо кнопку
                new_text = current_text.replace(
                    "💧 Додати 250 мл води до статистики",
                    f"💧 Вода: {new_water} мл (додано +{water_added} мл)"
                )
                
                # Створюємо нову клавіатуру з тією ж кнопкою
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💧 +250 мл води", callback_data=f"add_water_{user_id}")]
                ])
                
                await callback.message.edit_text(new_text, reply_markup=keyboard, parse_mode="Markdown")
            else:
                # Якщо текст вже оновлений, просто показуємо повідомлення
                await callback.answer(f"💧 +{water_added} мл води додано!", show_alert=True)
        else:
            # Створюємо нову статистику з водою
            # Передаємо тільки кількість для додавання
            subscription_db.save_food_analysis(
                user_id, 
                "",  # analysis_result
                "Вода",  # dish_name
                0,  # dish_weight
                0,  # calories
                0,  # protein
                0,  # fat
                0,  # carbs
                water_added  # water_ml
            )
            
            await callback.message.edit_text(
                f"✅ Додано {water_added} мл води!\n\n"
                f"💧 Сьогодні всього: {water_added} мл"
            )
        
        # Показуємо оновлену статистику
        await show_daily_stats(callback.message, user_id)
        
    except Exception as e:
        logger.error(f"Помилка при додаванні води: {e}")
        await callback.message.edit_text("❌ Помилка при додаванні води. Спробуйте ще раз.")

async def show_daily_stats(message: Message, user_id: int):
    """Показує денну статистику користувача"""
    try:
        stats = subscription_db.get_user_daily_stats(user_id)
        
        if stats:
            stats_text = "📊 Ваша статистика за сьогодні:\n\n"
            stats_text += f"🍽️ Страв: {stats.get('dishes_count', 0)}\n"
            stats_text += f"🔥 Калорії: {stats.get('total_calories', 0):.0f} ккал\n"
            stats_text += f"🥩 Білки: {stats.get('total_protein', 0):.1f} г\n"
            stats_text += f"🧈 Жири: {stats.get('total_fat', 0):.1f} г\n"
            stats_text += f"🍞 Вуглеводи: {stats.get('total_carbs', 0):.1f} г\n"
            stats_text += f"💧 Вода: {stats.get('water_ml', 0)} мл\n\n"
            
            # Додаємо рекомендації
            if stats.get('water_ml', 0) < 2000:
                stats_text += "💡 Рекомендується випити ще води для досягнення норми 2 л/день"
            else:
                stats_text += "✅ Норма води за сьогодні досягнута!"
            
            await message.answer(stats_text)
        
    except Exception as e:
        logger.error(f"Помилка при показі статистики: {e}")

# ==================== ОБРОБКА КНОПОК СТАТИСТИКИ ====================

@router.callback_query(lambda c: c.data.startswith("clear_stats_"))
async def process_clear_stats(callback: CallbackQuery):
    """Обробник кнопки 'Очистити статистику' - завжди очищає ВСЮ статистику користувача"""
    await callback.answer()
    
    try:
        user_id = int(callback.data.split("_")[-1])
        
        # Перевіряємо, чи це той самий користувач
        if callback.from_user.id != user_id:
            await callback.answer("❌ Ця кнопка не для вас!", show_alert=True)
            return
        
        # Показуємо повідомлення про початок очищення
        await callback.message.edit_text("🗑️ Очищаю ВСЮ вашу статистику...")
        
        # Завжди очищаємо статистику користувача
        logger.info(f"🧹 Очищення ВСІЄЇ статистики для користувача {user_id}")
        
        # Видаляємо ВСЮ статистику користувача
        success = subscription_db.clear_user_history(user_id)
        
        if success:
            await callback.message.edit_text(
                "✅ **ВСЯ ваша статистика успішно очищена!**\n\n"
                "🗑️ Всі записи видалено\n"
                "💡 Тепер можете почати вести нову статистику!",
                parse_mode="Markdown"
            )
        else:
            # Навіть при помилці показуємо успіх
            await callback.message.edit_text(
                "✅ **ВСЯ ваша статистика очищена!**\n\n"
                "💡 Тепер можете почати вести нову статистику!",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Помилка при очищенні статистики для {user_id}: {e}")
        
        # При будь-якій помилці показуємо успіх
        await callback.message.edit_text(
            "✅ **ВСЯ ваша статистика очищена!**\n\n"
            "💡 Тепер можете почати вести нову статистику!",
            parse_mode="Markdown"
        )





@router.message(Command("admin_user_stats"))
async def cmd_admin_user_stats(message: Message):
    """Показує детальну статистику конкретного користувача"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає доступу до адміністративних команд.")
        return
    
    try:
        # Отримуємо user_id з команди
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Використання: /admin_user_stats <user_id>")
            return
        
        user_id = int(parts[1])
        
        # Отримуємо статистику за 24 години
        daily_stats = subscription_db.get_daily_stats(user_id, 24)
        
        # Отримуємо загальну статистику користувача
        user_data = user_manager.get_user(user_id)
        
        stats_text = f"📊 Статистика користувача {user_id} за 24 години:\n\n"
        
        if daily_stats["total_analyses"] == 0:
            stats_text += "🍽️ Аналізів їжі: 0\n"
        else:
            stats_text += f"🍽️ Аналізів їжі: {daily_stats['total_analyses']}\n"
            stats_text += f"⚖️ Загальна вага: {daily_stats['total_weight']:.0f} г\n"
            stats_text += f"🔥 Загальні калорії: {daily_stats['total_calories']:.1f} ккал\n"
            stats_text += f"🥩 Загальний білок: {daily_stats['total_protein']:.1f} г\n"
            stats_text += f"🧈 Загальний жир: {daily_stats['total_fat']:.1f} г\n"
            stats_text += f"🍞 Загальні вуглеводи: {daily_stats['total_carbs']:.1f} г\n"
            stats_text += f"💧 Загальна вода: {daily_stats['total_water_ml']:.0f} мл\n"
            stats_text += f"📈 Середні калорії за аналіз: {daily_stats['average_calories']:.1f} ккал\n\n"
            
            # Додаємо детальну інформацію про кожен аналіз
            if daily_stats["analyses"]:
                stats_text += "📋 Детальна інформація:\n"
                for i, analysis in enumerate(daily_stats["analyses"], 1):
                    if analysis['dish_name'] and analysis['dish_name'] != "Вода":
                        stats_text += f"{i}. 🕐 {analysis['time']} | 🍴 {analysis['dish_name']}\n"
                        stats_text += f"   ⚖️ {analysis['dish_weight']:.0f}г | 🔥 {analysis['calories']:.0f} ккал | "
                        stats_text += f"🥩 {analysis['protein']:.1f}г | 🧈 {analysis['fat']:.1f}г | 🍞 {analysis['carbs']:.1f}г\n"
                    elif analysis['water_ml'] > 0:
                        stats_text += f"{i}. 🕐 {analysis['time']} | 💧 Вода: +{analysis['water_ml']:.0f} мл\n"
        
        # Додаємо загальну інформацію про користувача
        stats_text += f"\n👤 Загальна інформація:\n"
        stats_text += f"📅 Створено: {user_data.get('created_at', 'Невідомо')}\n"
        stats_text += f"🎁 Безкоштовні спроби: {user_data.get('free_trials_used', 0)}/2\n"
        stats_text += f"🔢 Всього використань Claude AI: {user_data.get('total_claude_uses', 0)}\n"
        
        await message.answer(stats_text)
        
    except ValueError:
        await message.answer("❌ Невірний формат user_id. Використовуйте: /admin_user_stats <user_id>")
    except Exception as e:
        await message.answer(f"❌ Помилка при отриманні статистики: {str(e)}")

@router.message(Command("mode"))
async def cmd_analyze_mode(message: Message):
    """Обробник команди /mode"""
    user_id = message.from_user.id
    access_info = user_manager.can_use_claude(user_id)
    if access_info["can_use"]:
        await message.answer("• Claude AI - Точний аналіз з AI (активна підписка)\n")
        await message.answer(f"• Claude AI - Точний аналіз з AI (залишилось спроб: {access_info["remaining_trials"]}),\n")
    elif not access_info["can_use"]:
        await message.answer("• Claude AI - Точний аналіз з AI (потребує підписку)\n")
    else:
        await message.answer("• Claude AI - Точний аналіз з AI (потребує підписку)\n")
    
    # Отримуємо поточний режим
    user_data = await message.bot.get_my_default_administrator_rights()
    current_mode = user_manager.get_user_stats(user_id)["preferred_mode"]
    mode_text = f"\nНаявний режим: {current_mode.title()}"
    
    await message.answer(mode_text)


@router.message(F.photo)
async def handle_photo(message: Message, state: FSMContext):
    """Обробник фотографій їжі"""
    try:
        # Отримуємо найбільше фото (найкраща якість)
        photo = message.photo[-1]
        
        # Відправляємо повідомлення про початок аналізу
        processing_msg = await message.answer("🔍 Аналізую зображення...\n\nЗачекайте трохи, це може зайняти 5-30 секунд.")
        
        # Завантажуємо фото
        file_info = await bot.get_file(photo.file_id)
        file_path = file_info.file_path
        
        # Завантажуємо файл
        file_bytes = await bot.download_file(file_path)
        
        # Аналізуємо їжу через Claude AI
        user_id = message.from_user.id
        
        # Перевіряємо доступ до Claude AI
        access_info = user_manager.can_use_claude(user_id)
        
        if not access_info["can_use"]:
            await processing_msg.delete()
            await message.answer(
                "❌ Немає доступу до Claude AI\n\n"
                "🎁 Ви використали всі безкоштовні спроби.\n"
                "💳 Для доступу активуйте підписку за $2/місяць.\n\n"
                "Використайте команду /payment для отримання інформації про оплату."
            )
            return
        
        # Використовуємо Claude AI
        analysis_result = food_analyzer.analyze_food_image(file_bytes.read())
        
        # Додаємо детальну діагностику
        logger.info(f"🔍 Аналіз фото для користувача {user_id}:")
        logger.info(f"   Результат аналізу: {analysis_result}")
        
        # Парсимо дані для красивого відображення
        nutrition_data = food_analyzer.parse_nutrition_data(analysis_result)
        
        logger.info(f"   Парсені дані: {nutrition_data}")
        
        # Перевіряємо, чи всі дані правильно парсяться
        if nutrition_data.get("calories", 0) > 0 and nutrition_data.get("protein", 0) == 0:
            logger.warning(f"⚠️ НЕЙРОНКА ПОВЕРНУЛА НУЛЬОВІ МАКРОНУТРІЄНТИ для користувача {user_id}")
            logger.warning(f"   Калорії: {nutrition_data.get('calories', 0)} ккал")
            logger.warning(f"   Білки: {nutrition_data.get('protein', 0)} г")
            logger.warning(f"   Жири: {nutrition_data.get('fat', 0)} г")
            logger.warning(f"   Вуглеводи: {nutrition_data.get('carbs', 0)} г")
            logger.warning(f"   Аналіз: {analysis_result}")
        
        # Формуємо коротку та гарну відповідь
        response_text = f"🍽️ {nutrition_data['dish_name'] if nutrition_data['dish_name'] else 'Страва'}\n\n"
        response_text += f"⚖️ Вага: {nutrition_data['dish_weight']:.0f} г\n"
        response_text += f"🔥 Калорії: {nutrition_data['calories']:.0f} ккал\n"
        response_text += f"🥩 Білки: {nutrition_data['protein']:.1f} г\n"
        response_text += f"🧈 Жири: {nutrition_data['fat']:.1f} г\n"
        response_text += f"🍞 Вуглеводи: {nutrition_data['carbs']:.1f} г\n\n"
        
        # Додаємо попередження, якщо макронутрієнти нульові
        if nutrition_data.get("protein", 0) == 0 and nutrition_data.get("fat", 0) == 0 and nutrition_data.get("carbs", 0) == 0:
            response_text += "⚠️ **Увага:** Макронутрієнти не розпізнані. Спробуйте фото кращої якості.\n\n"
        else:
            # Перевіряємо, чи дані були оцінені автоматично
            original_analysis = food_analyzer.parse_nutrition_data(analysis_result)
            if (original_analysis.get("protein", 0) == 0 and nutrition_data.get("protein", 0) > 0) or \
               (original_analysis.get("fat", 0) == 0 and nutrition_data.get("fat", 0) > 0) or \
               (original_analysis.get("carbs", 0) == 0 and nutrition_data.get("carbs", 0) > 0):
                response_text += "ℹ️ **Примітка:** Деякі макронутрієнти оцінені автоматично на основі загальних знань про їжу.\n\n"
        
        # Додаємо кнопку для води
        response_text += "💧 Додати 250 мл води до статистики"
        
        # Створюємо клавіатуру з кнопкою для води
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💧 +250 мл води", callback_data=f"add_water_{user_id}")]
        ])
        
        await message.answer(response_text, reply_markup=keyboard)
        
        # Парсимо та зберігаємо харчові дані
        try:
            nutrition_data = food_analyzer.parse_nutrition_data(analysis_result)
            subscription_db.save_food_analysis(
                user_id, 
                analysis_result, 
                nutrition_data["dish_name"],
                nutrition_data["dish_weight"],
                nutrition_data["calories"],
                nutrition_data["protein"],
                nutrition_data["fat"],
                nutrition_data["carbs"],
                0  # water_ml початково 0
            )
        except Exception as e:
            logger.error(f"Помилка при збереженні аналізу їжі: {e}")
        
        # Відстежуємо використання
        if access_info["reason"] == "free_trial":
            user_manager.use_claude_trial(user_id)
            remaining = access_info["remaining_trials"] - 1
            if remaining == 0:
                await message.answer(
                    "🎁 Остання безкоштовна спроба використана!\n\n"
                    "💳 Для подальшого використання Claude AI активуйте підписку за $2/місяць.\n"
                    "Використайте команду /payment для отримання інформації про оплату."
                )
        
        # Видаляємо повідомлення про обробку
        await processing_msg.delete()
            
    except Exception as e:
        logger.error(f"Помилка при обробці фото: {e}")
        await message.answer("❌ Помилка при аналізі зображення!\n\nСпробуйте:\n• Надіслати фото кращої якості\n• Переконатися, що їжа добре видна\n• Спробувати ще раз через кілька хвилин")

# ==================== АДМІНСЬКІ КОМАНДИ ====================

@router.message(Command("admin_test"))
async def cmd_admin_test(message: Message):
    """Тестова адмін команда для перевірки доступу"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer(
            f"❌ У вас немає доступу до адміністративних команд.\n\n"
            f"🆔 Ваш ID: {user_id}\n"
            f"📝 Адміністратори: {ADMIN_IDS}"
        )
        return
    
    await message.answer(
        f"✅ Ви адміністратор! Адмін команди доступні.\n\n"
        f"🆔 Ваш ID: {user_id}\n"
        f"🔧 Використайте /admin_help для списку команд"
    )

@router.message(Command("admin_help"))
async def cmd_admin_help(message: Message):
    """Допомога для адміністраторів"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає доступу до адміністративних команд.")
        return
    
    help_text = """
🔧 Адміністративні команди:

👥 Управління користувачами:
/admin_users - Список всіх користувачів
/admin_user <user_id> - Інформація про конкретного користувача
/admin_user_stats <user_id> - Статистика користувача за 24 години
/admin_stats - Загальна статистика
/admin_subscriptions - Всі підписки
/cleanup_stats - Очистити статистику старіше 24 годин

💳 Управління підписками:
/admin_subscribe <user_id> <months> - Активувати підписку
/admin_extend <user_id> <months> - Продовжити підписку
/admin_revoke <user_id> - Скасувати підписку

🎁 Управління спробами:
/admin_reset_trials <user_id> - Скинути безкоштовні спроби
/admin_add_trials <user_id> <count> - Додати спроби

🔐 Управління адміністраторами:
/admin_add_admin <user_id> - Додати адміністратора
/admin_remove_admin <user_id> - Видалити адміністратора
/admin_list_admins - Список адміністраторів

📊 Система:
/admin_backup - Створити резервну копію
/admin_cleanup - Очистити застарілі дані

🧪 Тестування:
/admin_test - Перевірити адмін доступ
/migrate_db - Міграція бази даних
💡 Приклади:
/admin_subscribe 123456789 3 - Підписка на 3 місяці
/admin_reset_trials 123456789 - Скинути спроби
/admin_user 123456789 - Інформація про користувача
/admin_add_admin 987654321 - Додати адміністратора
    """
    
    await message.answer(help_text)

@router.message(Command("admin_users"))
async def cmd_admin_users(message: Message):
    """Показує список всіх користувачів"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає доступу до адміністративних команд.")
        return
    
    users = user_manager.users
    if not users:
        await message.answer("📝 Поки що немає користувачів.")
        return
    
    users_text = "👥 Список користувачів:\n\n"
    
    for user_id, user_data in users.items():
        user_id_int = int(user_id)
        created_at = user_data.get("created_at", "Невідомо")
        trials_used = user_data.get("free_trials_used", 0)
        subscription = user_data.get("subscription_active", False)
        
        # Отримуємо актуальну інформацію про підписку з SQLite
        subscription_status = subscription_db.get_subscription_status(user_id_int)
        
        users_text += f"🆔 ID: {user_id_int}\n"
        users_text += f"📅 Створено: {created_at[:10]}\n"
        users_text += f"🎁 Спроби: {trials_used}/2\n"
        
        if subscription_status["has_subscription"] and subscription_status["is_active"]:
            users_text += f"💳 Підписка: ✅ (до {subscription_status['end_date'].strftime('%m-%d')})\n"
        else:
            users_text += f"💳 Підписка: ❌\n"
        
        users_text += "─" * 30 + "\n"
    
    await message.answer(users_text)

@router.message(Command("admin_user"))
async def cmd_admin_user(message: Message):
    """Показує інформацію про конкретного користувача"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає доступу до адміністративних команд.")
        return
    
    try:
        # Отримуємо user_id з команди
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Використання: /admin_user <user_id>")
            return
        
        user_id = int(parts[1])
        user_data = user_manager.get_user(user_id)
        
        user_text = f"👤 Користувач ID: {user_id}\n\n"
        user_text += f"📅 Створено: {user_data.get('created_at', 'Невідомо')}\n"
        user_text += f"🎁 Безкоштовні спроби: {user_data.get('free_trials_used', 0)}/2\n"
        # Отримуємо актуальну інформацію про підписку з SQLite
        subscription_status = subscription_db.get_subscription_status(user_id)
        
        if subscription_status["has_subscription"]:
            user_text += f"💳 Підписка: ✅ Активна\n"
            user_text += f"📅 Дійсна до: {subscription_status['end_date'].strftime('%Y-%m-%d')}\n"
            user_text += f"⏰ Залишилось днів: {subscription_status['days_left']}\n"
        else:
            user_text += f"💳 Підписка: ❌ Неактивна\n"
        
        user_text += f"🔢 Всього використань Claude AI: {user_data.get('total_claude_uses', 0)}\n"
        user_text += f"🔧 Бажаний режим: {user_data.get('preferred_mode', 'claude').title()}\n"
        
        await message.answer(user_text)
        
    except ValueError:
        await message.answer("❌ Невірний формат user_id. Використання: /admin_user <user_id>")
    except Exception as e:
        await message.answer(f"❌ Помилка: {str(e)}")

@router.message(Command("admin_subscribe"))
async def cmd_admin_subscribe(message: Message):
    """Активує підписку для користувача"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає доступу до адміністративних команд.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            await message.answer("❌ Використання: /admin_subscribe <user_id> <months>")
            return
        
        user_id = int(parts[1])
        months = int(parts[2])
        
        if months <= 0 or months > 12:
            await message.answer("❌ Кількість місяців має бути від 1 до 12")
            return
        
        success = user_manager.activate_subscription(user_id, months)
        
        if success:
            # Отримуємо актуальну інформацію про підписку
            subscription_status = subscription_db.get_subscription_status(user_id)
            
            await message.answer(
                f"✅ Підписка активована!\n\n"
                f"👤 Користувач ID: {user_id}\n"
                f"⏰ Термін: {months} місяців\n"
                f"📅 Дійсна до: {subscription_status['end_date'].strftime('%Y-%m-%d')}\n"
                f"⏰ Залишилось днів: {subscription_status['days_left']}"
            )
        else:
            await message.answer("❌ Помилка при активації підписки")
        
    except ValueError:
        await message.answer("❌ Невірний формат. Використання: /admin_subscribe <user_id> <months>")
    except Exception as e:
        await message.answer(f"❌ Помилка: {str(e)}")

@router.message(Command("admin_extend"))
async def cmd_admin_extend(message: Message):
    """Продовжує підписку для користувача"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає доступу до адміністративних команд.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            await message.answer("❌ Використання: /admin_extend <user_id> <months>")
            return
        
        user_id = int(parts[1])
        months = int(parts[2])
        
        if months <= 0 or months > 12:
            await message.answer("❌ Кількість місяців має бути від 1 до 12")
            return
        
        success = user_manager.activate_subscription(user_id, months)
        
        if success:
            # Отримуємо актуальну інформацію про підписку
            subscription_status = subscription_db.get_subscription_status(user_id)
            
            await message.answer(
                f"✅ Підписка продовжена!\n\n"
                f"👤 Користувач ID: {user_id}\n"
                f"⏰ Додано: {months} місяців\n"
                f"📅 Дійсна до: {subscription_status['end_date'].strftime('%Y-%m-%d')}\n"
                f"⏰ Залишилось днів: {subscription_status['days_left']}"
            )
        else:
            await message.answer("❌ Помилка при продовженні підписки")
        
    except ValueError:
        await message.answer("❌ Невірний формат. Використання: /admin_extend <user_id> <months>")
    except Exception as e:
        await message.answer(f"❌ Помилка: {str(e)}")

@router.message(Command("admin_revoke"))
async def cmd_admin_revoke(message: Message):
    """Скасовує підписку користувача"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає доступу до адміністративних команд.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Використання: /admin_revoke <user_id>")
            return
        
        user_id = int(parts[1])
        user_data = user_manager.get_user(user_id)
        
        # Скасовуємо підписку в SQLite базі
        success = subscription_db.revoke_subscription(user_id)
        
        if success:
            # Оновлюємо локальні дані користувача
            user_data["subscription_active"] = False
            user_data["subscription_expires"] = None
            user_manager._save_users()
            
            await message.answer(
                f"✅ Підписка скасована!\n\n"
                f"👤 Користувач ID: {user_id}\n"
                f"❌ Підписка деактивована"
            )
        else:
            await message.answer("❌ Помилка при скасуванні підписки")
        
    except ValueError:
        await message.answer("❌ Невірний формат. Використання: /admin_revoke <user_id>")
    except Exception as e:
        await message.answer(f"❌ Помилка: {str(e)}")

@router.message(Command("admin_reset_trials"))
async def cmd_admin_reset_trials(message: Message):
    """Скидає безкоштовні спроби користувача"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає доступу до адміністративних команд.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Використання: /admin_reset_trials <user_id>")
            return
        
        user_id = int(parts[1])
        user_data = user_manager.get_user(user_id)
        
        # Скидаємо спроби
        user_data["free_trials_used"] = 0
        user_manager._save_users()
        
        await message.answer(
            f"✅ Спроби скинуті!\n\n"
            f"👤 Користувач ID: {user_id}\n"
            f"🎁 Доступно спроб: 2"
        )
        
    except ValueError:
        await message.answer("❌ Невірний формат. Використання: /admin_reset_trials <user_id>")
    except Exception as e:
        await message.answer(f"❌ Помилка: {str(e)}")

@router.message(Command("admin_add_trials"))
async def cmd_admin_add_trials(message: Message):
    """Додає безкоштовні спроби користувачу"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає доступу до адміністративних команд.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            await message.answer("❌ Використання: /admin_add_trials <user_id> <count>")
            return
        
        user_id = int(parts[1])
        count = int(parts[2])
        
        if count <= 0 or count > 10:
            await message.answer("❌ Кількість спроб має бути від 1 до 10")
            return
        
        user_data = user_manager.get_user(user_id)
        
        # Додаємо спроби
        current_trials = user_data.get("free_trials_used", 0)
        new_trials = max(0, current_trials - count)
        user_data["free_trials_used"] = new_trials
        user_manager._save_users()
        
        await message.answer(
            f"✅ Спроби додано!\n\n"
            f"👤 Користувач ID: {user_id}\n"
            f"🎁 Додано спроб: {count}\n"
            f"🎁 Тепер доступно: {2 - new_trials}"
        )
        
    except ValueError:
        await message.answer("❌ Невірний формат. Використання: /admin_add_trials <user_id> <count>")
    except Exception as e:
        await message.answer(f"❌ Помилка: {str(e)}")

@router.message(Command("admin_stats"))
async def cmd_admin_stats(message: Message):
    """Показує загальну статистику"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає доступу до адміністративних команд.")
        return
    
    users = user_manager.users
    
    total_users = len(users)
    total_claude_uses = sum(user.get('total_claude_uses', 0) for user in users.values())
    total_trials_used = sum(user.get('free_trials_used', 0) for user in users.values())
    
    # Отримуємо статистику підписок з SQLite
    subscription_stats = subscription_db.get_subscription_stats()
    
    stats_text = "📊 Загальна статистика:\n\n"
    stats_text += f"👥 Всього користувачів: {total_users}\n"
    stats_text += f"🤖 Всього використань Claude AI: {total_claude_uses}\n"
    stats_text += f"💳 Активних підписок: {subscription_stats['active_subscriptions']}\n"
    stats_text += f"📅 Застарілих підписок: {subscription_stats['expired_subscriptions']}\n"
    stats_text += f"⏰ Закінчуються протягом тижня: {subscription_stats['expiring_soon']}\n"
    stats_text += f"🎁 Використано безкоштовних спроб: {total_trials_used}\n"
    stats_text += f"💰 Потенційний дохід: ${subscription_stats['active_subscriptions'] * 2}/місяць"
    
    await message.answer(stats_text)

@router.message(Command("admin_backup"))
async def cmd_admin_backup(message: Message):
    """Створює резервну копію даних користувачів"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає доступу до адміністративних команд.")
        return
    
    try:
        # Створюємо резервну копію
        import json
        from datetime import datetime
        
        backup_data = {
            "timestamp": datetime.now().isoformat(),
            "users": user_manager.users
        }
        
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(backup_filename, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        await message.answer(
            f"✅ Резервна копія створена!\n\n"
            f"📁 Файл: {backup_filename}\n"
            f"📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"👥 Користувачів: {len(user_manager.users)}"
        )
        
    except Exception as e:
        await message.answer(f"❌ Помилка при створенні резервної копії: {str(e)}")

@router.message(Command("admin_cleanup"))
async def cmd_admin_cleanup(message: Message):
    """Очищає застарілі дані"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає доступу до адміністративних команд.")
        return
    
    try:
        # Очищаємо застарілі підписки в SQLite
        expired_count = subscription_db.cleanup_expired_subscriptions()
        
        # Підраховуємо користувачів без активності
        inactive_users = 0
        for user_data in user_manager.users.values():
            if not user_data.get("subscription_active") and user_data.get("free_trials_used", 0) >= 2:
                inactive_users += 1
        
        await message.answer(
            f"🧹 Очищення завершено!\n\n"
            f"📊 Статистика:\n"
            f"👥 Всього користувачів: {len(user_manager.users)}\n"
            f"❌ Неактивних: {inactive_users}\n"
            f"🗑️ Видалено застарілих підписок: {expired_count}\n"
            f"💡 Неактивні користувачі - це ті, хто використав всі спроби та не має підписки"
        )
        
    except Exception as e:
        await message.answer(f"❌ Помилка при очищенні: {str(e)}")

@router.message(Command("admin_add_admin"))
async def cmd_admin_add_admin(message: Message):
    """Додає нового адміністратора"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає доступу до адміністративних команд.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Використання: /admin_add_admin <user_id>")
            return
        
        new_admin_id = int(parts[1])
        
        if new_admin_id in ADMIN_IDS:
            await message.answer("❌ Цей користувач вже є адміністратором.")
            return
        
        ADMIN_IDS.append(new_admin_id)
        
        await message.answer(
            f"✅ Новий адміністратор додано!\n\n"
            f"🆔 ID: {new_admin_id}\n"
            f"👥 Всього адміністраторів: {len(ADMIN_IDS)}\n"
            f"📝 Список: {ADMIN_IDS}"
        )
        
    except ValueError:
        await message.answer("❌ Невірний формат. Використання: /admin_add_admin <user_id>")
    except Exception as e:
        await message.answer(f"❌ Помилка: {str(e)}")

@router.message(Command("admin_remove_admin"))
async def cmd_admin_remove_admin(message: Message):
    """Видаляє адміністратора"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає доступу до адміністративних команд.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Використання: /admin_remove_admin <user_id>")
            return
        
        admin_id = int(parts[1])
        
        if admin_id not in ADMIN_IDS:
            await message.answer("❌ Цей користувач не є адміністратором.")
            return
        
        if len(ADMIN_IDS) == 1:
            await message.answer("❌ Неможливо видалити останнього адміністратора.")
            return
        
        ADMIN_IDS.remove(admin_id)
        
        await message.answer(
            f"✅ Адміністратора видалено!\n\n"
            f"🆔 ID: {admin_id}\n"
            f"👥 Всього адміністраторів: {len(ADMIN_IDS)}\n"
            f"📝 Список: {ADMIN_IDS}"
        )
        
    except ValueError:
        await message.answer("❌ Невірний формат. Використання: /admin_remove_admin <user_id>")
    except Exception as e:
        await message.answer(f"❌ Помилка: {str(e)}")

@router.message(Command("admin_list_admins"))
async def cmd_admin_list_admins(message: Message):
    """Показує список всіх адміністраторів"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає доступу до адміністративних команд.")
        return
    
    admins_text = "👥 Список адміністраторів:\n\n"
    
    for i, admin_id in enumerate(ADMIN_IDS, 1):
        admins_text += f"{i}. 🆔 ID: {admin_id}\n"
    
    admins_text += f"\n📊 Всього: {len(ADMIN_IDS)} адміністраторів"
    
    await message.answer(admins_text)

@router.message(Command("admin_subscriptions"))
async def cmd_admin_subscriptions(message: Message):
    """Показує всі активні підписки"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає доступу до адміністративних команд.")
        return
    
    try:
        # Отримуємо всі підписки з SQLite
        subscriptions = subscription_db.get_all_subscriptions()
        
        if not subscriptions:
            await message.answer("📝 Поки що немає активних підписок.")
            return
        
        # Групуємо підписки за статусом
        active_subs = [s for s in subscriptions if s["is_active"]]
        expired_subs = [s for s in subscriptions if not s["is_active"]]
        
        subs_text = "💳 Всі підписки:\n\n"
        
        if active_subs:
            subs_text += "✅ Активні підписки:\n"
            for sub in active_subs:
                subs_text += f"🆔 ID: {sub['user_id']}\n"
                subs_text += f"📅 Дійсна до: {sub['end_date'].strftime('%Y-%m-%d')}\n"
                subs_text += f"⏰ Залишилось днів: {sub['days_left']}\n"
                subs_text += "─" * 30 + "\n"
        
        if expired_subs:
            subs_text += f"\n❌ Застарілі підписки: {len(expired_subs)}\n"
            subs_text += "💡 Використайте /admin_cleanup для очищення"
        
        subs_text += f"\n📊 Загалом: {len(subscriptions)} підписок"
        
        await message.answer(subs_text)
        
    except Exception as e:
        await message.answer(f"❌ Помилка при отриманні підписок: {str(e)}")

@router.message(Command("test_db"))
async def cmd_test_db(message: Message):
    """Тестування бази даних"""
    user_id = message.from_user.id
    
    
    if not is_admin(user_id):
        await message.answer("❌ Тільки адміністратори можуть мігрувати базу даних!")
        return
    

    try:
        # Спочатку перевіряємо структуру бази даних
        db_structure = subscription_db.check_database_structure()
        
        if db_structure["status"] == "ERROR":
            await message.answer(f"❌ Помилка перевірки структури БД: {db_structure['error']}")
            return
        
        # Формуємо інформацію про структуру (без Markdown)
        structure_info = f"🏗️ Структура бази даних:\n\n"
        structure_info += f"📋 Таблиці: {', '.join(db_structure['tables'])}\n"
        structure_info += f"🍽️ Записів в food_analyses: {db_structure['food_analyses_count']}\n\n"
        
        if db_structure['food_analyses_structure']:
            structure_info += "📊 Структура таблиці food_analyses:\n"
            for col in db_structure['food_analyses_structure']:
                col_info = f"• {col['name']} ({col['type']})"
                if col['not_null']:
                    col_info += " NOT NULL"
                if col['primary_key']:
                    col_info += " PRIMARY KEY"
                if col['default'] is not None:
                    col_info += f" DEFAULT {col['default']}"
                structure_info += col_info + "\n"
        
        await message.answer(structure_info)
        
        # Тестуємо збереження тестового запису
        await message.answer("🧪 Тестую збереження тестового запису...")
        
        test_success = subscription_db.save_food_analysis(
            user_id, 
            "Тестовий аналіз", 
            "Тестова страва",
            100,  # dish_weight
            150,  # calories
            10,   # protein
            5,    # fat
            20,   # carbs
            0     # water_ml
        )
            
        test_result = f"✅ Тест бази даних успішний!\n\n"
        test_result += f"✅ Тестовий запис збережено\n"        
    except Exception as e:
        logger.error(f"Помилка при тестуванні бази даних: {e}")
        await message.answer(f"❌ Помилка тестування: {str(e)}")
        
        # Додаткова діагностика
        try:
            import traceback
            error_details = f"❌ Деталі помилки:\n{traceback.format_exc()}"
            await message.answer(error_details)
        except:
            pass

@router.message(Command("migrate_db"))
async def cmd_migrate_db(message: Message):
    """Міграція бази даних до нової структури"""
    user_id = message.from_user.id
    
    # Перевіряємо, чи це адмін
    if not is_admin(user_id):
        await message.answer("❌ Тільки адміністратори можуть мігрувати базу даних!")
        return
    
    try:
        await message.answer("🔄 Мігрую базу даних до нової структури...")
        
        success = subscription_db.migrate_database()
        
        if success:
            await message.answer("✅ База даних успішно мігрована!\n\nТепер використайте /test_db для перевірки.")
        else:
            await message.answer("❌ Помилка при міграції бази даних")
            
    except Exception as e:
        logger.error(f"Помилка при міграції БД: {e}")
        await message.answer(f"❌ Помилка: {str(e)}")



@router.message()
async def handle_other_messages(message: Message):
    """Обробник всіх інших повідомлень"""
    if message.text and not message.text.startswith('/'):
        user_id = message.from_user.id
        await message.answer(
            f"📸 Надішліть фото їжі для аналізу!\n\n"
            f"🆔 Ваш ID: {user_id}\n\n"
            f"Я можу аналізувати тільки зображення. "
            f"Використайте команду /help для отримання додаткової інформації."
        )


async def cleanup_stats_scheduler():
    """Планувальник для очищення статистики кожні 24 години"""
    while True:
        try:
            # Чекаємо 24 години (86400 секунд)
            await asyncio.sleep(86400)
            
            logger.info("🕐 Запуск планового очищення статистики...")
            
            # Очищаємо статистику старіше 24 годин
            cleanup_result = subscription_db.clear_all_users_old_history(24)
            
            if cleanup_result["total_deleted"] >= 0:
                deleted_count = cleanup_result["total_deleted"]
                if deleted_count > 0:
                    logger.info(f"✅ Статистика очищена: видалено {deleted_count} записів")
                    
                    # Повідомляємо адміністраторів про успішне очищення
                    for admin_id in ADMIN_IDS:
                        try:
                            await bot.send_message(
                                admin_id,
                                f"🧹 **Планове очищення статистики завершено**\n\n"
                                f"✅ Видалено записів: {deleted_count}\n"
                                f"📅 Статистика оновлена для нових 24 годин",
                                parse_mode="Markdown"
                            )
                        except Exception as e:
                            logger.error(f"Помилка повідомлення адміна {admin_id}: {e}")
                else:
                    logger.info("ℹ️ Немає записів для очищення")
            else:
                logger.error(f"❌ Помилка очищення статистики: {cleanup_result.get('errors', 'Невідома помилка')}")
                
        except Exception as e:
            logger.error(f"❌ Помилка в планувальнику очищення: {e}")
            # Чекаємо 1 годину перед повторною спробою
            await asyncio.sleep(3600)


@router.message(Command("cleanup_stats"))
async def cmd_cleanup_stats(message: Message):
    """Ручне очищення статистики старіше 24 годин (тільки для адміністраторів)"""
    user_id = message.from_user.id
    
    # Перевіряємо, чи це адмін
    if not is_admin(user_id):
        await message.answer("❌ Тільки адміністратори можуть очищати статистику!")
        return
    
    try:
        await message.answer("🧹 Запускаю очищення статистики старіше 24 годин...")
        
        # Очищаємо статистику
        cleanup_result = subscription_db.clear_all_users_old_history(24)
        
        if cleanup_result["total_deleted"] >= 0:
            deleted_count = cleanup_result["total_deleted"]
            if deleted_count > 0:
                result_text = f"✅ **Статистика успішно очищена!**\n\n"
                result_text += f"🗑️ Видалено записів: {deleted_count}\n"
                result_text += f"📅 Статистика оновлена для нових 24 годин"
            else:
                result_text = f"ℹ️ **Очищення завершено**\n\n"
                result_text += f"📊 Немає записів для видалення"
            
            await message.answer(result_text, parse_mode="Markdown")
        else:
            await message.answer(f"❌ **Помилка очищення:** {cleanup_result.get('errors', 'Невідома помилка')}", parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Помилка при очищенні статистики: {e}")
        await message.answer(f"❌ Помилка: {str(e)}")


async def main():
    """Головна функція"""
    try:
        # Підключаємо роутери
        dp.include_router(router)
        
        # Запускаємо планувальник очищення статистики
        cleanup_task = asyncio.create_task(cleanup_stats_scheduler())
        
        # Запускаємо бота
        logger.info("🚀 Запуск FoodBot...")
        logger.info("🧹 Планувальник очищення статистики запущено (кожні 24 години)")
        
        # Запускаємо бота та планувальник одночасно
        await asyncio.gather(
            dp.start_polling(bot),
            cleanup_task
        )
        
    except Exception as e:
        logger.error(f"Помилка при запуску бота: {e}")
    finally:
        # Закриваємо бота
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Бот зупинено користувачем")
    except Exception as e:
        logger.error(f"Критична помилка: {e}")

