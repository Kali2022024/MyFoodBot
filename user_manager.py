import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from subscription_db import subscription_db

class UserManager:
    """Менеджер користувачів з системою безкоштовних спроб та платним доступом"""
    
    def __init__(self, data_file: str = "users.json"):
        self.data_file = data_file
        self.users = self._load_users()
    
    def _load_users(self) -> Dict:
        """Завантажує дані користувачів з файлу"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def _save_users(self):
        """Зберігає дані користувачів у файл"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Помилка збереження користувачів: {e}")
    
    def get_user(self, user_id: int) -> Dict:
        """Отримує або створює користувача"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.users:
            # Створюємо нового користувача
            self.users[user_id_str] = {
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "free_trials_used": 0,
                "max_free_trials": 2,
                "subscription_active": False,
                "subscription_expires": None,
                "total_claude_uses": 0,
                "preferred_mode": "claude"
            }
            self._save_users()
        
        return self.users[user_id_str]
    
    def can_use_claude(self, user_id: int) -> Dict:
        """Перевіряє, чи може користувач використовувати Claude AI"""
        user = self.get_user(user_id)
        
        # Перевіряємо активну підписку в SQLite базі
        subscription_status = subscription_db.get_subscription_status(user_id)
        
        if subscription_status["has_subscription"] and subscription_status["is_active"]:
            return {
                "can_use": True,
                "reason": "subscription",
                "remaining_trials": None,
                "subscription_expires": subscription_status["end_date"]
            }
        
        # Перевіряємо безкоштовні спроби
        remaining_trials = user["max_free_trials"] - user["free_trials_used"]
        
        if remaining_trials > 0:
            return {
                "can_use": True,
                "reason": "free_trial",
                "remaining_trials": remaining_trials,
                "subscription_expires": None
            }
        
        return {
            "can_use": False,
            "reason": "no_access",
            "remaining_trials": 0,
            "subscription_expires": None
        }
    
    def use_claude_trial(self, user_id: int):
        """Використовує безкоштовну спробу Claude AI"""
        user = self.get_user(user_id)
        user["free_trials_used"] += 1
        user["total_claude_uses"] += 1
        self._save_users()
    
    def activate_subscription(self, user_id: int, months: int = 1):
        """Активує платну підписку"""
        # Використовуємо SQLite базу даних для підписок
        success = subscription_db.add_subscription(user_id, months)
        
        if success:
            # Оновлюємо локальні дані користувача
            user = self.get_user(user_id)
            user["subscription_active"] = True
            # Отримуємо актуальну дату закінчення з бази
            subscription_status = subscription_db.get_subscription_status(user_id)
            if subscription_status["has_subscription"]:
                user["subscription_expires"] = subscription_status["end_date"].isoformat()
            self._save_users()
        
        return success
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Отримує статистику користувача"""
        user = self.get_user(user_id)
        
        return {
            "free_trials_used": user["free_trials_used"],
            "max_free_trials": user["max_free_trials"],
            "remaining_trials": user["max_free_trials"] - user["free_trials_used"],
            "subscription_active": user.get("subscription_active", False),
            "subscription_expires": user.get("subscription_expires"),
            "total_claude_uses": user["total_claude_uses"],
            "preferred_mode": user.get("preferred_mode", "claude")
        }
    
    def set_preferred_mode(self, user_id: int, mode: str):
        """Встановлює бажаний режим аналізу"""
        user = self.get_user(user_id)
        user["preferred_mode"] = mode
        self._save_users()
    
    def get_payment_info(self) -> str:
        """Повертає інформацію про оплату"""
        return """
💳 Інформація про оплату Claude AI:

💰 Вартість: $2 на місяць
🎁 Безкоштовні спроби: 2 спроби для кожного користувача
⏰ Термін дії: 30 днів з моменту оплати

💳 Способи оплати:
• PayPal
• Кредитні картки
• Криптовалюти

📧 Для оплати зверніться до: @onopandrey
        """
    
    def get_subscription_status_message(self, user_id: int) -> str:
        """Повертає повідомлення про статус підписки"""
        stats = self.get_user_stats(user_id)
        access_info = self.can_use_claude(user_id)
        
        message = "🔐 Статус доступу до Claude AI:\n\n"
        
        if access_info["can_use"]:
            if access_info["reason"] == "subscription":
                expires = access_info["subscription_expires"]
                days_left = (expires - datetime.now()).days
                message += f"✅ Активна підписка\n"
                message += f"📅 Дійсна до: {expires.strftime('%d.%m.%Y')}\n"
                message += f"⏰ Залишилось днів: {days_left}\n"
            else:
                message += f"🎁 Безкоштовна спроба\n"
                message += f"🔢 Залишилось спроб: {access_info['remaining_trials']}\n"
        else:
            message += "❌ Немає доступу\n"
            message += f"🎁 Використано безкоштовних спроб: {stats['free_trials_used']}/{stats['max_free_trials']}\n"
            message += "💳 Для доступу активуйте підписку\n\n"
            message += "💰 Вартість: $2 на місяць\n"
            message += "📧 Зв'яжіться з адміністратором: @onopandrey"
        
        message += f"\n\n📊 Загальна статистика:\n"
        message += f"• Використано Claude AI: {stats['total_claude_uses']} разів\n"
        message += f"• Бажаний режим: {stats['preferred_mode'].title()}"
        
        return message
