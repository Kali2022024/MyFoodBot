#!/usr/bin/env python3
"""
Скрипт для міграції існуючих підписок з JSON в SQLite
"""

import json
import os
import sys
from datetime import datetime
from subscription_db import subscription_db

def migrate_subscriptions():
    """Мігрує існуючі підписки з JSON в SQLite"""
    print("🔄 Міграція підписок з JSON в SQLite...\n")
    
    # Шлях до файлу користувачів
    users_file = "users.json"
    
    if not os.path.exists(users_file):
        print("❌ Файл users.json не знайдено!")
        print("💡 Переконайтеся, що ви знаходитесь в правильній директорії")
        return False
    
    try:
        # Завантажуємо дані користувачів
        with open(users_file, 'r', encoding='utf-8') as f:
            users_data = json.load(f)
        
        print(f"📊 Знайдено {len(users_data)} користувачів")
        
        migrated_count = 0
        skipped_count = 0
        
        for user_id_str, user_data in users_data.items():
            user_id = int(user_id_str)
            
            # Перевіряємо, чи є активна підписка
            if user_data.get("subscription_active") and user_data.get("subscription_expires"):
                try:
                    # Парсимо дату закінчення
                    expires_str = user_data["subscription_expires"]
                    expires_date = datetime.fromisoformat(expires_str)
                    
                    # Перевіряємо, чи не закінчилася підписка
                    if expires_date > datetime.now():
                        # Розраховуємо кількість місяців
                        now = datetime.now()
                        days_diff = (expires_date - now).days
                        months = max(1, round(days_diff / 30))
                        
                        # Мігруємо підписку
                        success = subscription_db.add_subscription(user_id, months)
                        
                        if success:
                            migrated_count += 1
                            print(f"✅ Мігровано підписку для користувача {user_id} (до {expires_date.strftime('%Y-%m-%d')})")
                        else:
                            print(f"❌ Помилка міграції підписки для користувача {user_id}")
                            skipped_count += 1
                    else:
                        print(f"⏰ Пропущено застарілу підписку для користувача {user_id}")
                        skipped_count += 1
                        
                except Exception as e:
                    print(f"❌ Помилка обробки підписки користувача {user_id}: {e}")
                    skipped_count += 1
            else:
                # Немає підписки
                skipped_count += 1
        
        print(f"\n📊 Результат міграції:")
        print(f"   ✅ Мігровано: {migrated_count} підписок")
        print(f"   ⏭️ Пропущено: {skipped_count} користувачів")
        
        # Показуємо статистику після міграції
        stats = subscription_db.get_subscription_stats()
        print(f"\n📈 Статистика після міграції:")
        print(f"   • Всього підписок: {stats['total_subscriptions']}")
        print(f"   • Активних: {stats['active_subscriptions']}")
        print(f"   • Застарілих: {stats['expired_subscriptions']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Помилка міграції: {e}")
        return False

def main():
    """Головна функція"""
    print("🚀 Запуск міграції підписок...\n")
    
    try:
        success = migrate_subscriptions()
        
        if success:
            print("\n✅ Міграція завершена успішно!")
            print("🔧 Тепер всі підписки зберігаються в SQLite")
            print("💡 Старі дані JSON залишаються для зворотної сумісності")
        else:
            print("\n❌ Міграція завершена з помилками!")
            print("🔍 Перевірте логи та налаштування")
            
    except Exception as e:
        print(f"\n💥 Критична помилка при міграції: {e}")
        return False
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
