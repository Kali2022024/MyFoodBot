import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import threading
import time
import contextlib

logger = logging.getLogger(__name__)

class SubscriptionDB:
    """Клас для роботи з базою даних підписок"""
    
    def __init__(self, db_path: str = "subscriptions.db"):
        """Ініціалізація бази даних"""
        self.db_path = db_path
        self.lock = threading.Lock()  # Для потокобезпеки
        self._init_database()
    
    @contextlib.contextmanager
    def _get_connection(self, timeout: int = 30, max_retries: int = 3):
        """
        Контекстний менеджер для безпечного отримання з'єднання з базою даних
        
        Args:
            timeout: Таймаут для з'єднання в секундах
            max_retries: Максимальна кількість спроб підключення
        """
        conn = None
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Створюємо з'єднання з таймаутом та WAL режимом
                conn = sqlite3.connect(
                    self.db_path,
                    timeout=timeout,
                    check_same_thread=False
                )
                
                # Включаємо WAL режим для кращої продуктивності та меншого блокування
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                conn.execute("PRAGMA temp_store=MEMORY")
                
                # Встановлюємо режим ізоляції
                conn.isolation_level = None  # Автоматичні транзакції
                
                yield conn
                break
                
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and retry_count < max_retries - 1:
                    retry_count += 1
                    wait_time = (2 ** retry_count) * 0.1  # Експоненціальна затримка
                    logger.warning(f"🔄 База даних заблокована, спроба {retry_count}/{max_retries}. "
                                 f"Очікую {wait_time:.1f}с...")
                    time.sleep(wait_time)
                    
                    if conn:
                        try:
                            conn.close()
                        except:
                            pass
                    continue
                else:
                    raise
            except Exception as e:
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                raise
        else:
            if conn:
                try:
                    conn.close()
                except:
                    pass
            raise sqlite3.OperationalError("database is locked after all retries")
    
    def _execute_with_retry(self, operation, *args, **kwargs):
        """
        Виконує операцію з базою даних з retry логікою
        
        Args:
            operation: Функція для виконання
            *args, **kwargs: Аргументи для функції
            
        Returns:
            Результат виконання операції
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                with self.lock:
                    with self._get_connection() as conn:
                        return operation(conn, *args, **kwargs)
                        
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and retry_count < max_retries - 1:
                    retry_count += 1
                    wait_time = (2 ** retry_count) * 0.1
                    logger.warning(f"🔄 Операція заблокована, спроба {retry_count}/{max_retries}. "
                                 f"Очікую {wait_time:.1f}с...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise
            except Exception as e:
                logger.error(f"❌ Помилка виконання операції: {e}")
                raise
    
    def cleanup_database(self):
        """
        Очищає базу даних від заблокованих з'єднань та оптимізує її
        """
        def cleanup_operation(conn):
            cursor = conn.cursor()
            
            # Очищаємо WAL файли
            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            
            # Оновлюємо статистику
            cursor.execute("ANALYZE")
            
            # Очищаємо кеш
            cursor.execute("PRAGMA cache_size=10000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            
            conn.commit()
            logger.info("🧹 База даних очищена та оптимізована")
            return True
        
        try:
            return self._execute_with_retry(cleanup_operation)
        except Exception as e:
            logger.error(f"❌ Помилка очищення бази даних: {e}")
            return False
    
    def get_database_status(self) -> Dict:
        """
        Отримує статус бази даних
        
        Returns:
            Dict: Статус бази даних
        """
        def status_operation(conn):
            cursor = conn.cursor()
            status = {}
            
            # Перевіряємо режим журналу
            cursor.execute("PRAGMA journal_mode")
            status['journal_mode'] = cursor.fetchone()[0]
            
            # Перевіряємо синхронізацію
            cursor.execute("PRAGMA synchronous")
            status['synchronous'] = cursor.fetchone()[0]
            
            # Перевіряємо розмір кешу
            cursor.execute("PRAGMA cache_size")
            status['cache_size'] = cursor.fetchone()[0]
            
            # Перевіряємо кількість таблиць
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            status['tables'] = [row[0] for row in cursor.fetchall()]
            
            # Перевіряємо розмір бази даних
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            status['database_size'] = cursor.fetchone()[0]
            
            return status
        
        try:
            return self._execute_with_retry(status_operation)
        except Exception as e:
            logger.error(f"❌ Помилка отримання статусу бази даних: {e}")
            return {}
    
    def force_unlock_database(self):
        """
        Примусово розблоковує базу даних (використовувати тільки в критичних випадках)
        """
        try:
            # Закриваємо всі можливі з'єднання
            import gc
            gc.collect()
            
            # Очищаємо WAL файли
            import os
            wal_file = f"{self.db_path}-wal"
            if os.path.exists(wal_file):
                try:
                    os.remove(wal_file)
                    logger.info("🗑️ WAL файл видалено")
                except:
                    pass
            
            # Очищаємо журнал
            journal_file = f"{self.db_path}-journal"
            if os.path.exists(journal_file):
                try:
                    os.remove(journal_file)
                    logger.info("🗑️ Журнал видалено")
                except:
                    pass
            
            logger.info("🔓 База даних примусово розблокована")
            return True
            
        except Exception as e:
            logger.error(f"❌ Помилка примусового розблоковування: {e}")
            return False
    
    def _init_database(self):
        """Ініціалізація бази даних та створення таблиць"""
        def init_tables(conn):
            cursor = conn.cursor()
            
            # Створюємо таблицю підписок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    user_id INTEGER PRIMARY KEY,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            # Створюємо таблицю аналізів їжі
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS food_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    analysis_text TEXT NOT NULL,
                    dish_name TEXT DEFAULT '',
                    dish_weight REAL DEFAULT 0,
                    calories REAL DEFAULT 0,
                    protein REAL DEFAULT 0,
                    fat REAL DEFAULT 0,
                    carbs REAL DEFAULT 0,
                    water_ml REAL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # Створюємо індекси для швидкого пошуку
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_end_date 
                ON subscriptions(end_date)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_id 
                ON subscriptions(user_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_food_user_date 
                ON food_analyses(user_id, created_at)
            ''')
            
            conn.commit()
        
        try:
            self._execute_with_retry(init_tables)
            logger.info("✅ База даних підписок ініціалізована")
        except Exception as e:
            logger.error(f"❌ Помилка ініціалізації бази даних: {e}")
            raise
    
    def add_subscription(self, user_id: int, months: int = 1) -> bool:
        """
        Додає або оновлює підписку користувача
        
        Args:
            user_id: ID користувача
            months: Кількість місяців підписки
            
        Returns:
            bool: True якщо успішно, False якщо помилка
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                now = datetime.now()
                start_date = now
                
                # Перевіряємо, чи є активна підписка
                cursor.execute(
                    "SELECT end_date FROM subscriptions WHERE user_id = ?",
                    (user_id,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Продовжуємо існуючу підписку
                    current_end = datetime.fromisoformat(existing[0])
                    if current_end > now:
                        # Підписка ще активна, додаємо місяці
                        end_date = current_end + timedelta(days=30 * months)
                    else:
                        # Підписка закінчилася, створюємо нову
                        end_date = now + timedelta(days=30 * months)
                    
                    cursor.execute('''
                        UPDATE subscriptions 
                        SET end_date = ?, updated_at = ?
                        WHERE user_id = ?
                    ''', (end_date.isoformat(), now.isoformat(), user_id))
                    
                else:
                    # Створюємо нову підписку
                    end_date = now + timedelta(days=30 * months)
                    cursor.execute('''
                        INSERT INTO subscriptions 
                        (user_id, start_date, end_date, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        user_id, 
                        start_date.isoformat(), 
                        end_date.isoformat(),
                        now.isoformat(),
                        now.isoformat()
                    ))
                
                conn.commit()
                conn.close()
                
                logger.info(f"✅ Підписка для користувача {user_id} активована до {end_date.strftime('%Y-%m-%d')}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Помилка додавання підписки для {user_id}: {e}")
            return False
    
    def get_subscription_status(self, user_id: int) -> Dict:
        """
        Отримує статус підписки користувача
        
        Args:
            user_id: ID користувача
            
        Returns:
            Dict: Статус підписки
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT start_date, end_date, created_at, updated_at
                    FROM subscriptions 
                    WHERE user_id = ?
                ''', (user_id,))
                
                result = cursor.fetchone()
                conn.close()
                
                if not result:
                    return {
                        "has_subscription": False,
                        "start_date": None,
                        "end_date": None,
                        "days_left": 0,
                        "is_active": False
                    }
                
                start_date = datetime.fromisoformat(result[0])
                end_date = datetime.fromisoformat(result[1])
                created_at = datetime.fromisoformat(result[2])
                updated_at = datetime.fromisoformat(result[3])
                
                now = datetime.now()
                days_left = (end_date - now).days
                is_active = end_date > now
                
                return {
                    "has_subscription": True,
                    "start_date": start_date,
                    "end_date": end_date,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "days_left": max(0, days_left),
                    "is_active": is_active
                }
                
        except Exception as e:
            logger.error(f"❌ Помилка отримання статусу підписки для {user_id}: {e}")
            return {
                "has_subscription": False,
                "start_date": None,
                "end_date": None,
                "days_left": 0,
                "is_active": False
            }
    
    def revoke_subscription(self, user_id: int) -> bool:
        """
        Скасовує підписку користувача
        
        Args:
            user_id: ID користувача
            
        Returns:
            bool: True якщо успішно, False якщо помилка
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute(
                    "DELETE FROM subscriptions WHERE user_id = ?",
                    (user_id,)
                )
                
                conn.commit()
                conn.close()
                
                logger.info(f"✅ Підписка для користувача {user_id} скасована")
                return True
                
        except Exception as e:
            logger.error(f"❌ Помилка скасування підписки для {user_id}: {e}")
            return False
    
    def cleanup_expired_subscriptions(self) -> int:
        """
        Очищає застарілі підписки
        
        Returns:
            int: Кількість видалених підписок
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                now = datetime.now()
                
                # Знаходимо застарілі підписки
                cursor.execute(
                    "SELECT user_id FROM subscriptions WHERE end_date < ?",
                    (now.isoformat(),)
                )
                
                expired_users = cursor.fetchall()
                expired_count = len(expired_users)
                
                if expired_count > 0:
                    # Видаляємо застарілі підписки
                    cursor.execute(
                        "DELETE FROM subscriptions WHERE end_date < ?",
                        (now.isoformat(),)
                    )
                    
                    conn.commit()
                    logger.info(f"🧹 Видалено {expired_count} застарілих підписок")
                
                conn.close()
                return expired_count
        
        except Exception as e:
            logger.error(f"❌ Помилка очищення застарілих підписок: {e}")
            return 0
    
    def save_food_analysis(self, user_id: int, analysis_text: str, dish_name: str = "", 
                          dish_weight: float = 0, calories: float = 0, protein: float = 0, 
                          fat: float = 0, carbs: float = 0, water_ml: float = 0) -> bool:
        """
        Зберігає аналіз їжі користувача
        
        Args:
            user_id: ID користувача
            analysis_text: Текст аналізу
            dish_name: Назва страви
            dish_weight: Приблизна вага страви (грами)
            calories: Калорії
            protein: Білки (грами)
            fat: Жири (грами)
            carbs: Вуглеводи (грами)
            water_ml: Кількість води (мл)
            
        Returns:
            bool: True якщо успішно, False якщо помилка
        """
        try:
            logger.info(f"🔍 Спроба збереження аналізу їжі для користувача {user_id}")
            logger.info(f"📝 Дані: dish_name='{dish_name}', calories={calories}, protein={protein}, fat={fat}, carbs={carbs}, water_ml={water_ml}")
            
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                now = datetime.now()
                
                # Логуємо SQL запит
                sql_query = '''
                    INSERT INTO food_analyses 
                    (user_id, analysis_text, dish_name, dish_weight, calories, protein, fat, carbs, water_ml, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                params = (user_id, analysis_text, dish_name, dish_weight, calories, protein, fat, carbs, water_ml, now.isoformat())
                
                logger.info(f"🔍 SQL запит: {sql_query}")
                logger.info(f"🔍 Параметри: {params}")
                
                cursor.execute(sql_query, params)
                
                # Отримуємо ID вставленого запису
                inserted_id = cursor.lastrowid
                logger.info(f"✅ Запис вставлено з ID: {inserted_id}")
                
                conn.commit()
                conn.close()
                
                logger.info(f"✅ Аналіз їжі збережено для користувача {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Помилка збереження аналізу їжі для {user_id}: {e}")
            logger.error(f"❌ Тип помилки: {type(e).__name__}")
            logger.error(f"❌ Деталі помилки: {str(e)}")
            
            # Додаткова діагностика
            try:
                import traceback
                logger.error(f"❌ Stack trace: {traceback.format_exc()}")
            except:
                pass
                
            return False
    

    

    
    def add_water(self, user_id: int, water_ml: float = 250) -> bool:
        """
        Додає воду до статистики користувача
        
        Args:
            user_id: ID користувача
            water_ml: Кількість води в мл (за замовчуванням 250)
            
        Returns:
            bool: True якщо успішно, False якщо помилка
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                now = datetime.now()
                
                cursor.execute('''
                    INSERT INTO food_analyses 
                    (user_id, analysis_text, dish_name, dish_weight, calories, protein, fat, carbs, water_ml, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, "Вода", "Вода", 0, 0, 0, 0, 0, water_ml, now.isoformat()))
                
                conn.commit()
                conn.close()
                
                logger.info(f"✅ Вода ({water_ml} мл) додана для користувача {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Помилка додавання води для {user_id}: {e}")
            return False
    
    def clear_user_history(self, user_id: int) -> bool:
        """
        Очищає всю історію аналізів їжі користувача
        
        Args:
            user_id: ID користувача
            
        Returns:
            bool: True якщо успішно, False якщо помилка
        """
        def clear_history_operation(conn, user_id):
            cursor = conn.cursor()
            
            # Спочатку перевіряємо, скільки записів буде видалено
            cursor.execute('SELECT COUNT(*) FROM food_analyses WHERE user_id = ?', (user_id,))
            records_to_delete = cursor.fetchone()[0]
            
            if records_to_delete == 0:
                logger.info(f"ℹ️ Немає записів для видалення для користувача {user_id}")
                return True
            
            # Видаляємо всі записи користувача
            cursor.execute('DELETE FROM food_analyses WHERE user_id = ?', (user_id,))
            deleted_count = cursor.rowcount
            
            # Таблиця daily_stats не існує в нашій схемі, тому пропускаємо її
            
            conn.commit()
            
            logger.info(f"✅ Історія користувача {user_id} очищена ({deleted_count} записів)")
            return True
        
        try:
            return self._execute_with_retry(clear_history_operation, user_id)
        except Exception as e:
            logger.error(f"❌ Помилка очищення історії для {user_id}: {e}")
            return False



    def clear_all_users_old_history(self, hours: int = 24) -> Dict[str, int]:
        """
        Автоматично очищає стару історію для всіх користувачів
        
        Args:
            hours: Кількість годин для очищення (за замовчуванням 24)
            
        Returns:
            Dict: Статистика очищення {"total_users": X, "total_deleted": Y, "errors": Z}
        """
        try:
            logger.info(f"🔄 Починаю автоматичне очищення старої історії для всіх користувачів (залишаю тільки останні {hours} годин)")
            
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Розраховуємо час N годин тому
                cutoff_time = datetime.now() - timedelta(hours=hours)
                logger.info(f"🔍 Час відсічення: {cutoff_time.isoformat()}")
                
                # Отримуємо список всіх унікальних користувачів
                cursor.execute('SELECT DISTINCT user_id FROM food_analyses')
                all_users = [row[0] for row in cursor.fetchall()]
                logger.info(f"🔍 Знайдено користувачів: {len(all_users)}")
                
                if not all_users:
                    logger.info("ℹ️ Немає користувачів для очищення")
                    conn.close()
                    return {"total_users": 0, "total_deleted": 0, "errors": 0}
                
                total_deleted = 0
                errors = 0
                
                # Очищаємо історію для кожного користувача
                for user_id in all_users:
                    try:
                        # Перевіряємо, скільки записів буде видалено для цього користувача
                        cursor.execute('''
                            SELECT COUNT(*) FROM food_analyses 
                            WHERE user_id = ? AND created_at < ?
                        ''', (user_id, cutoff_time.isoformat()))
                        
                        user_records_to_delete = cursor.fetchone()[0]
                        
                        if user_records_to_delete > 0:
                            # Видаляємо старі записи для користувача
                            cursor.execute('''
                                DELETE FROM food_analyses 
                                WHERE user_id = ? AND created_at < ?
                            ''', (user_id, cutoff_time.isoformat()))
                            
                            deleted_count = cursor.rowcount
                            total_deleted += deleted_count
                            
                            logger.info(f"✅ Користувач {user_id}: видалено {deleted_count} старих записів")
                        else:
                            logger.info(f"ℹ️ Користувач {user_id}: немає старих записів для видалення")
                            
                    except Exception as e:
                        errors += 1
                        logger.error(f"❌ Помилка очищення для користувача {user_id}: {e}")
                
                # Підтверджуємо зміни
                conn.commit()
                conn.close()
                
                logger.info(f"✅ Автоматичне очищення завершено: {len(all_users)} користувачів, {total_deleted} записів видалено, {errors} помилок")
                
                return {
                    "total_users": len(all_users),
                    "total_deleted": total_deleted,
                    "errors": errors
                }
                
        except Exception as e:
            logger.error(f"❌ Критична помилка автоматичного очищення: {e}")
            return {"total_users": 0, "total_deleted": 0, "errors": 1}

    def get_user_daily_stats(self, user_id: int) -> Optional[Dict]:
        """
        Отримує денну статистику користувача
        
        Args:
            user_id: ID користувача
            
        Returns:
            Dict: Статистика за сьогодні або None
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                now = datetime.now()
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = today_start + timedelta(days=1)
                
                # Отримуємо всі записи за сьогодні
                cursor.execute('''
                    SELECT dish_name, dish_weight, calories, protein, fat, carbs, water_ml
                    FROM food_analyses 
                    WHERE user_id = ? AND created_at BETWEEN ? AND ?
                ''', (user_id, today_start.isoformat(), today_end.isoformat()))
                
                records = cursor.fetchall()
                conn.close()
                
                if not records:
                    return None
                
                # Підраховуємо загальну статистику
                total_calories = 0
                total_protein = 0
                total_fat = 0
                total_carbs = 0
                total_water = 0
                dishes_count = 0
                
                for record in records:
                    dish_name, weight, calories, protein, fat, carbs, water = record
                    
                    # Рахуємо тільки страви (не воду)
                    if dish_name != "Вода" and calories > 0:
                        dishes_count += 1
                        total_calories += calories or 0
                        total_protein += protein or 0
                        total_fat += fat or 0
                        total_carbs += carbs or 0
                    
                    # Рахуємо воду окремо
                    total_water += water or 0
                
                return {
                    "dishes_count": dishes_count,
                    "total_calories": total_calories,
                    "total_protein": total_protein,
                    "total_fat": total_fat,
                    "total_carbs": total_carbs,
                    "water_ml": total_water
                }
                
        except Exception as e:
            logger.error(f"❌ Помилка отримання денної статистики для користувача {user_id}: {e}")
            return None

    def update_user_water(self, user_id: int, water_ml: float) -> bool:
        """
        Додає воду до існуючої кількості для користувача за сьогодні
        
        Args:
            user_id: ID користувача
            water_ml: Кількість води в мл для додавання
            
        Returns:
            bool: True якщо успішно, False якщо помилка
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                now = datetime.now()
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = today_start + timedelta(days=1)
                
                # Перевіряємо, чи є запис за сьогодні
                cursor.execute('''
                    SELECT id, water_ml FROM food_analyses 
                    WHERE user_id = ? AND created_at BETWEEN ? AND ?
                    LIMIT 1
                ''', (user_id, today_start.isoformat(), today_end.isoformat()))
                
                existing_record = cursor.fetchone()
                
                if existing_record:
                    # Отримуємо поточну кількість води
                    current_water = existing_record[1] or 0
                    new_total_water = current_water + water_ml
                    
                    # Оновлюємо існуючий запис, ДОДАВАЮЧИ воду
                    cursor.execute('''
                        UPDATE food_analyses 
                        SET water_ml = ? 
                        WHERE id = ?
                    ''', (new_total_water, existing_record[0]))
                    
                    logger.info(f"✅ Вода додана для користувача {user_id}: {current_water} + {water_ml} = {new_total_water} мл")
                else:
                    # Створюємо новий запис з водою
                    cursor.execute('''
                        INSERT INTO food_analyses 
                        (user_id, analysis_text, dish_name, dish_weight, calories, protein, fat, carbs, water_ml, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (user_id, "", "Вода", 0, 0, 0, 0, 0, water_ml, now.isoformat()))
                    
                    logger.info(f"✅ Новий запис води створено для користувача {user_id}: {water_ml} мл")
                
                conn.commit()
                conn.close()
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Помилка оновлення води для користувача {user_id}: {e}")
            return False
    
    def get_all_subscriptions(self) -> List[Dict]:
        """
        Отримує всі активні підписки
        
        Returns:
            List[Dict]: Список всіх підписок
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT user_id, start_date, end_date, created_at, updated_at
                    FROM subscriptions 
                    ORDER BY end_date DESC
                ''')
                
                results = cursor.fetchall()
                conn.close()
                
                subscriptions = []
                for result in results:
                    subscriptions.append({
                        "user_id": result[0],
                        "start_date": datetime.fromisoformat(result[1]),
                        "end_date": datetime.fromisoformat(result[2]),
                        "created_at": datetime.fromisoformat(result[3]),
                        "updated_at": datetime.fromisoformat(result[4]),
                        "days_left": max(0, (datetime.fromisoformat(result[2]) - datetime.now()).days),
                        "is_active": datetime.fromisoformat(result[2]) > datetime.now()
                    })
                
                return subscriptions
                
        except Exception as e:
            logger.error(f"❌ Помилка отримання всіх підписок: {e}")
            return []
    


    def check_database_structure(self) -> Dict:
        """
        Перевіряє структуру бази даних та створює таблиці, якщо вони відсутні
        
        Returns:
            Dict: Статус перевірки
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Перевіряємо, чи існують таблиці
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                # Перевіряємо структуру таблиці food_analyses
                food_analyses_structure = []
                food_count = 0
                required_columns = ['id', 'user_id', 'analysis_text', 'dish_name', 'dish_weight', 'calories', 'protein', 'fat', 'carbs', 'water_ml', 'created_at']
                
                if 'food_analyses' in tables:
                    cursor.execute("PRAGMA table_info(food_analyses)")
                    columns = cursor.fetchall()
                    current_columns = [col[1] for col in columns]
                    
                    for col in columns:
                        food_analyses_structure.append({
                            "name": col[1],
                            "type": col[2],
                            "not_null": bool(col[3]),
                            "default": col[4],
                            "primary_key": bool(col[5])
                        })
                    
                    # Перевіряємо кількість записів
                    cursor.execute("SELECT COUNT(*) FROM food_analyses")
                    food_count = cursor.fetchone()[0]
                    
                    # Перевіряємо відсутні колонки
                    missing_columns = [col for col in required_columns if col not in current_columns]
                    
                    if missing_columns:
                        logger.warning(f"⚠️ Відсутні колонки в food_analyses: {missing_columns}")
                        return {
                            "tables": tables,
                            "food_analyses_structure": food_analyses_structure,
                            "food_analyses_count": food_count,
                            "status": "NEEDS_MIGRATION",
                            "missing_columns": missing_columns,
                            "message": f"Потрібна міграція. Відсутні колонки: {', '.join(missing_columns)}"
                        }
                
                conn.close()
                
                # Якщо таблиці відсутні, створюємо їх
                if 'subscriptions' not in tables or 'food_analyses' not in tables:
                    logger.warning("⚠️ Деякі таблиці відсутні. Спроба створення...")
                    self._init_database()
                    return {
                        "tables": ["subscriptions", "food_analyses"],
                        "food_analyses_structure": [],
                        "food_analyses_count": 0,
                        "status": "OK",
                        "message": "Таблиці створені"
                    }
                
                return {
                    "tables": tables,
                    "food_analyses_structure": food_analyses_structure,
                    "food_analyses_count": food_count,
                    "status": "OK",
                    "message": "База даних має правильну структуру"
                }
                
        except Exception as e:
            logger.error(f"❌ Помилка перевірки структури бази даних: {e}")
            return {
                "status": "ERROR",
                "error": str(e)
            }

    def migrate_database(self) -> bool:
        """
        Мігрує існуючу базу даних до нової структури
        
        Returns:
            bool: True якщо успішно, False якщо помилка
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Перевіряємо поточну структуру
                cursor.execute("PRAGMA table_info(food_analyses)")
                columns = [col[1] for col in cursor.fetchall()]
                
                logger.info(f"🔍 Поточна структура food_analyses: {columns}")
                
                # Якщо відсутні необхідні колонки, додаємо їх
                if 'dish_name' not in columns:
                    logger.info("➕ Додаю колонку dish_name")
                    cursor.execute("ALTER TABLE food_analyses ADD COLUMN dish_name TEXT DEFAULT ''")
                
                if 'dish_weight' not in columns:
                    logger.info("➕ Додаю колонку dish_weight")
                    cursor.execute("ALTER TABLE food_analyses ADD COLUMN dish_weight REAL DEFAULT 0")
                
                if 'water_ml' not in columns:
                    logger.info("➕ Додаю колонку water_ml")
                    cursor.execute("ALTER TABLE food_analyses ADD COLUMN water_ml REAL DEFAULT 0")
                
                conn.commit()
                conn.close()
                
                logger.info("✅ Міграція бази даних завершена")
                return True
                
        except Exception as e:
            logger.error(f"❌ Помилка міграції бази даних: {e}")
            return False



# Глобальний екземпляр бази даних
subscription_db = SubscriptionDB()
