import base64
import io
from anthropic import Anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

class FoodAnalyzer:
    """Клас для аналізу їжі за допомогою Claude AI"""
    
    def __init__(self):
        """Ініціалізація клієнта Anthropic"""
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = CLAUDE_MODEL
    
    def analyze_food_image(self, image_bytes: bytes) -> str:
        """
        Аналізує зображення їжі та повертає інформацію про калорії, білки та вуглеводи
        
        Args:
            image_bytes: Байти зображення
            
        Returns:
            str: Аналіз їжі з детальною інформацією
        """
        try:
            # Конвертуємо зображення в base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Промпт для аналізу їжі
            prompt = """
            Проаналізуй це зображення їжі та надай точну інформацію у строго визначеному форматі:
            
            Назва страви: [конкретна назва]
            Вага: [число] г
            Калорії: [число] ккал
            Білки: [число] г
            Жири: [число] г
            Вуглеводи: [число] г
            
            ВАЖЛИВО:
            - Давай ТОЧНІ числові значення, не приблизні
            - Якщо не можеш точно визначити, вказуй найбільш ймовірне значення
            - Використовуй тільки числа та одиниці виміру (г, ккал)
            - Не додавай зайвих слів або пояснень
            - Відповідай українською мовою
            
            Приклад правильної відповіді:
            Назва страви: Рисова страва з овочами та яйцем
            Вага: 200 г
            Калорії: 400 ккал
            Білки: 12 г
            Жири: 8 г
            Вуглеводи: 65 г
            """
            
            # Відправляємо запит до Claude з зображенням
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_base64
                                }
                            }
                        ]
                    }
                ]
            )
            
            # Повертаємо відповідь
            return message.content[0].text
            
        except Exception as e:
            error_msg = f"❌ Помилка при аналізі зображення: {str(e)}"
            print(f"Помилка FoodAnalyzer: {e}")
            return error_msg
    
    def parse_nutrition_data(self, analysis_text: str) -> dict:
        """
        Парсить текст аналізу та витягує числові дані про харчування
        
        Args:
            analysis_text: Текст аналізу їжі
            
        Returns:
            Dict: Словник з числовими даними
        """
        try:
            import re
            
            # Ініціалізуємо значення за замовчуванням
            nutrition_data = {
                "dish_name": "",
                "dish_weight": 0.0,
                "calories": 0.0,
                "protein": 0.0,
                "fat": 0.0,
                "carbs": 0.0
            }
            
            # Шукаємо назву страви (перший рядок або після "Це" / "This is")
            dish_patterns = [
                r'^(.*?)(?:\n|\.|ккал|calories)',
                r'(?:Це|This is)\s+(.*?)(?:\n|\.|ккал|calories)',
                r'^(.*?)(?:\s+\d+\s*ккал|\s+\d+\s*kcal)'
            ]
            
            for pattern in dish_patterns:
                match = re.search(pattern, analysis_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    dish_name = match.group(1).strip()
                    if dish_name and len(dish_name) > 3:
                        nutrition_data["dish_name"] = dish_name
                        break
            
            # Шукаємо вагу страви
            weight_patterns = [
                r'вага[:\s]*(\d+(?:\.\d+)?)\s*(?:г|грам|грамів|g|gram)',
                r'(\d+(?:\.\d+)?)\s*(?:г|грам|грамів|g|gram)\s*(?:вага|weight)',
                r'weight[:\s]*(\d+(?:\.\d+)?)\s*(?:g|gram)',
                r'(\d+(?:\.\d+)?)\s*(?:g|gram)\s*weight',
                r'приблизно\s*(\d+(?:\.\d+)?)\s*(?:г|грам|g)',
                r'approximately\s*(\d+(?:\.\d+)?)\s*(?:g|gram)'
            ]
            
            for pattern in weight_patterns:
                match = re.search(pattern, analysis_text, re.IGNORECASE)
                if match:
                    nutrition_data["dish_weight"] = float(match.group(1))
                    break
            
            # Якщо вага не знайдена, оцінюємо приблизно за калоріями
            if nutrition_data["dish_weight"] == 0 and nutrition_data["calories"] > 0:
                # Приблизна оцінка: 1 ккал ≈ 1.5-2 г їжі
                estimated_weight = nutrition_data["calories"] * 1.8
                nutrition_data["dish_weight"] = estimated_weight
            elif nutrition_data["dish_weight"] == 0:
                # Якщо немає ні ваги, ні калорій, встановлюємо стандартну вагу
                nutrition_data["dish_weight"] = 200.0
            
            # Шукаємо калорії (різні формати)
            calorie_patterns = [
                r'(\d+(?:\.\d+)?)\s*(?:ккал|калорій|калорії|kcal|calories)',
                r'калорій[:\s]*(\d+(?:\.\d+)?)',
                r'(\d+(?:\.\d+)?)\s*ккал',
                r'calories[:\s]*(\d+(?:\.\d+)?)',
                r'(\d+(?:\.\d+)?)\s*calories'
            ]
            
            for pattern in calorie_patterns:
                match = re.search(pattern, analysis_text, re.IGNORECASE)
                if match:
                    nutrition_data["calories"] = float(match.group(1))
                    break
            
            # Шукаємо білки
            protein_patterns = [
                r'білк[аи]*[:\s]*(\d+(?:\.\d+)?)\s*(?:г|грам|грамів|g|gram)',
                r'(\d+(?:\.\d+)?)\s*(?:г|грам|грамів|g|gram)\s*білк[аи]*',
                r'protein[:\s]*(\d+(?:\.\d+)?)\s*(?:g|gram)',
                r'(\d+(?:\.\d+)?)\s*(?:g|gram)\s*protein'
            ]
            
            for pattern in protein_patterns:
                match = re.search(pattern, analysis_text, re.IGNORECASE)
                if match:
                    nutrition_data["protein"] = float(match.group(1))
                    break
            
            # Шукаємо жири
            fat_patterns = [
                r'жир[аи]*[:\s]*(\d+(?:\.\d+)?)\s*(?:г|грам|грамів|g|gram)',
                r'(\d+(?:\.\d+)?)\s*(?:г|грам|грамів|g|gram)\s*жир[аи]*',
                r'fat[:\s]*(\d+(?:\.\d+)?)\s*(?:g|gram)',
                r'(\d+(?:\.\d+)?)\s*(?:g|gram)\s*fat'
            ]
            
            for pattern in fat_patterns:
                match = re.search(pattern, analysis_text, re.IGNORECASE)
                if match:
                    nutrition_data["fat"] = float(match.group(1))
                    break
            
            # Шукаємо вуглеводи
            carbs_patterns = [
                r'вуглевод[аи]*[:\s]*(\d+(?:\.\d+)?)\s*(?:г|грам|грамів|g|gram)',
                r'(\d+(?:\.\d+)?)\s*(?:г|грам|грамів|g|gram)\s*вуглевод[аи]*',
                r'carb[аи]*[:\s]*(\d+(?:\.\d+)?)\s*(?:g|gram)',
                r'(\d+(?:\.\d+)?)\s*(?:g|gram)\s*carb[аи]*'
            ]
            
            for pattern in carbs_patterns:
                match = re.search(pattern, analysis_text, re.IGNORECASE)
                if match:
                    nutrition_data["carbs"] = float(match.group(1))
                    break
            
            # Додаткова валідація та покращення результатів
            self._validate_and_improve_nutrition_data(nutrition_data, analysis_text)
            
            return nutrition_data
            
        except Exception as e:
            print(f"Помилка парсингу харчових даних: {e}")
            return {
                "dish_name": "",
                "dish_weight": 0.0,
                "calories": 0.0,
                "protein": 0.0,
                "fat": 0.0,
                "carbs": 0.0
            }
    
    def _validate_and_improve_nutrition_data(self, nutrition_data: dict, analysis_text: str):
        """
        Валідує та покращує дані про харчування на основі загальних знань про їжу
        """
        try:
            # Якщо калорії є, але макронутрієнти нульові, намагаємося оцінити їх
            if nutrition_data["calories"] > 0:
                total_calories = nutrition_data["calories"]
                
                # Якщо білки нульові, оцінюємо на основі загальних пропорцій
                if nutrition_data["protein"] == 0:
                    # Типова пропорція: білки 15-25% від калорій
                    # 1г білка = 4 ккал
                    estimated_protein = (total_calories * 0.2) / 4
                    nutrition_data["protein"] = round(estimated_protein, 1)
                
                # Якщо жири нульові, оцінюємо на основі загальних пропорцій
                if nutrition_data["fat"] == 0:
                    # Типова пропорція: жири 20-35% від калорій
                    # 1г жиру = 9 ккал
                    estimated_fat = (total_calories * 0.25) / 9
                    nutrition_data["fat"] = round(estimated_fat, 1)
                
                # Якщо вуглеводи нульові, оцінюємо на основі загальних пропорцій
                if nutrition_data["carbs"] == 0:
                    # Типова пропорція: вуглеводи 45-65% від калорій
                    # 1г вуглеводів = 4 ккал
                    estimated_carbs = (total_calories * 0.55) / 4
                    nutrition_data["carbs"] = round(estimated_carbs, 1)
                
                # Перевіряємо, чи сума калорій від макронутрієнтів приблизно співпадає
                calculated_calories = (nutrition_data["protein"] * 4 + 
                                     nutrition_data["fat"] * 9 + 
                                     nutrition_data["carbs"] * 4)
                
                # Якщо різниця занадто велика, коригуємо пропорції
                if abs(calculated_calories - total_calories) > total_calories * 0.3:
                    # Коригуємо пропорції, щоб сума була ближче до загальних калорій
                    ratio = total_calories / calculated_calories
                    nutrition_data["protein"] = round(nutrition_data["protein"] * ratio, 1)
                    nutrition_data["fat"] = round(nutrition_data["fat"] * ratio, 1)
                    nutrition_data["carbs"] = round(nutrition_data["carbs"] * ratio, 1)
            
            # Додаткова перевірка на основі назви страви
            dish_name = nutrition_data["dish_name"].lower()
            if "рис" in dish_name or "rice" in dish_name:
                if nutrition_data["carbs"] < 10:
                    nutrition_data["carbs"] = max(nutrition_data["carbs"], 30)
            elif "яйц" in dish_name or "egg" in dish_name:
                if nutrition_data["protein"] < 5:
                    nutrition_data["protein"] = max(nutrition_data["protein"], 12)
            elif "овоч" in dish_name or "vegetable" in dish_name:
                if nutrition_data["carbs"] < 5:
                    nutrition_data["carbs"] = max(nutrition_data["carbs"], 8)
            
        except Exception as e:
            print(f"Помилка при валідації даних: {e}")
            pass
    
    def get_health_tips(self, food_analysis: str) -> str:
        """
        Генерує корисні поради щодо здорового харчування на основі аналізу
        
        Args:
            food_analysis: Результат аналізу їжі
            
        Returns:
            str: Корисні поради
        """
        try:
            prompt = f"""
            На основі цього аналізу їжі:
            
            {food_analysis}
            
            Надай 3-5 корисних порад щодо здорового харчування, які стосуються цієї страви.
            Поради мають бути практичними та корисними.
            
            Відповідай українською мовою у форматі списку.
            """
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            return message.content[0].text
            
        except Exception as e:
            error_msg = f"❌ Помилка при генерації порад: {str(e)}"
            print(f"Помилка get_health_tips: {e}")
            return error_msg
