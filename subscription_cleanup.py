#!/usr/bin/env python3
"""
Скрипт для автоматичного очищення застарілих підписок та старої історії аналізів їжі
Запускається через cron або як окремий процес
"""

import time
import logging
from subscription_db import subscription_db

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('subscription_cleanup.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def cleanup_expired_subscriptions():
    """Очищає застарілі підписки"""
    try:
        logger.info("🧹 Початок очищення застарілих підписок...")
        
        # Очищаємо застарілі підписки
        expired_count = subscription_db.cleanup_expired_subscriptions()
        
        if expired_count > 0:
            logger.info(f"✅ Видалено {expired_count} застарілих підписок")
        else:
            logger.info("✅ Застарілих підписок не знайдено")
        
        # Отримуємо статистику
        stats = subscription_db.get_subscription_stats()
        logger.info(f"📊 Статистика підписок:")
        logger.info(f"   • Всього: {stats['total_subscriptions']}")
        logger.info(f"   • Активних: {stats['active_subscriptions']}")
        logger.info(f"   • Застарілих: {stats['expired_subscriptions']}")
        logger.info(f"   • Закінчуються протягом тижня: {stats['expiring_soon']}")
        
        return expired_count
        
    except Exception as e:
        logger.error(f"❌ Помилка при очищенні підписок: {e}")
        return 0

def cleanup_old_food_history():
    """Очищає стару історію аналізів їжі (старіше 24 годин)"""
    try:
        logger.info("🍽️ Початок очищення старої історії аналізів їжі...")
        
        # Очищаємо стару історію для всіх користувачів (старіше 24 годин)
        cleanup_stats = subscription_db.clear_all_users_old_history(24)
        
        if cleanup_stats['total_deleted'] > 0:
            logger.info(f"✅ Очищено історію для {cleanup_stats['total_users']} користувачів")
            logger.info(f"   • Всього записів видалено: {cleanup_stats['total_deleted']}")
            logger.info(f"   • Помилок: {cleanup_stats['errors']}")
        else:
            logger.info("✅ Старої історії аналізів їжі не знайдено")
        
        return cleanup_stats['total_deleted']
        
    except Exception as e:
        logger.error(f"❌ Помилка при очищенні старої історії їжі: {e}")
        return 0

def main():
    """Головна функція"""
    logger.info("🚀 Запуск скрипта очищення...")
    
    try:
        # Очищаємо застарілі підписки
        expired_count = cleanup_expired_subscriptions()
        
        # Очищаємо стару історію аналізів їжі
        old_history_count = cleanup_old_food_history()
        
        logger.info(f"✅ Очищення завершено.")
        logger.info(f"   • Видалено підписок: {expired_count}")
        logger.info(f"   • Видалено записів історії: {old_history_count}")
        
    except KeyboardInterrupt:
        logger.info("⏹️ Скрипт зупинено користувачем")
    except Exception as e:
        logger.error(f"❌ Критична помилка: {e}")
    finally:
        # Закриваємо з'єднання з базою даних
        subscription_db.close()
        logger.info("🔒 З'єднання з базою даних закрито")

if __name__ == "__main__":
    main()
