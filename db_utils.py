import aiosqlite
import os
import logging
from typing import Dict, Any, Optional, List, Tuple, Union

# Путь к БД
DB_PATH = os.getenv("DB_PATH", "BD_ONA.db")

# Настройка логирования
logger = logging.getLogger(__name__)

# Импорт функции railway_print для логирования
try:
    from railway_logging import railway_print
except ImportError:
    # Определяем функцию railway_print, если модуль railway_logging не найден
    def railway_print(message, level="INFO"):
        prefix = "ИНФО"
        if level.upper() == "ERROR":
            prefix = "ОШИБКА"
        elif level.upper() == "WARNING":
            prefix = "ПРЕДУПРЕЖДЕНИЕ"
        elif level.upper() == "DEBUG":
            prefix = "ОТЛАДКА"
        print(f"{prefix}: {message}")
        import sys
        sys.stdout.flush()

async def init_db():
    """
    Инициализирует базу данных, проверяет существование таблиц
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем, существуют ли все необходимые таблицы
            result = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN "
                "('users', 'surveys', 'questions', 'options', 'user_answers')"
            )
            existing_tables = [row[0] async for row in result]
            
            # Проверяем, все ли необходимые таблицы существуют
            required_tables = ['users', 'surveys', 'questions', 'options', 'user_answers']
            missing_tables = [table for table in required_tables if table not in existing_tables]
            
            if not missing_tables:
                railway_print("База данных SQLite инициализирована успешно", "INFO")
                return True
            else:
                railway_print(f"Отсутствуют таблицы: {', '.join(missing_tables)}", "WARNING")
                return False
    except Exception as e:
        railway_print(f"Ошибка при инициализации базы данных: {e}", "ERROR")
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        return False

async def save_user(user_id: int, username: Optional[str], full_name: Optional[str]):
    """
    Сохраняет информацию о пользователе в базу данных
    
    Args:
        user_id: ID пользователя в Telegram
        username: Имя пользователя в Telegram (может быть None)
        full_name: Полное имя пользователя (может быть None)
    
    Returns:
        bool: True, если операция успешна, False в противном случае
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем, существует ли пользователь
            async with db.execute(
                "SELECT user_id FROM users WHERE user_id = ?", 
                (user_id,)
            ) as cursor:
                user_exists = await cursor.fetchone()
            
            if user_exists:
                # Обновляем информацию о пользователе
                await db.execute(
                    "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
                    (username, full_name, user_id)
                )
                railway_print(f"Обновлена информация о пользователе {user_id}", "INFO")
            else:
                # Добавляем нового пользователя
                await db.execute(
                    "INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
                    (user_id, username, full_name)
                )
                railway_print(f"Добавлен новый пользователь {user_id}", "INFO")
            
            await db.commit()
            return True
    except Exception as e:
        railway_print(f"Ошибка при сохранении пользователя: {e}", "ERROR")
        logger.error(f"Ошибка при сохранении пользователя: {e}")
        return False

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Получает информацию о пользователе из базы данных
    
    Args:
        user_id: ID пользователя в Telegram
    
    Returns:
        Optional[Dict[str, Any]]: Словарь с данными пользователя или None, если пользователь не найден
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE user_id = ?", 
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    except Exception as e:
        railway_print(f"Ошибка при получении пользователя: {e}", "ERROR")
        logger.error(f"Ошибка при получении пользователя: {e}")
        return None

async def save_survey_answers(user_id: int, answers: Dict[int, Union[str, int]]):
    """
    Сохраняет ответы на опрос в базу данных
    
    Args:
        user_id: ID пользователя в Telegram
        answers: Словарь ответов на вопросы {question_id: answer}
    
    Returns:
        bool: True, если операция успешна, False в противном случае
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Удаляем предыдущие ответы пользователя, если они есть
            await db.execute(
                "DELETE FROM user_answers WHERE user_id = ?", 
                (user_id,)
            )
            
            # Сохраняем новые ответы
            for question_id, answer in answers.items():
                # Если ответ - строка, сохраняем как текст
                if isinstance(answer, str):
                    await db.execute(
                        "INSERT INTO user_answers (user_id, question_id, answer_text) VALUES (?, ?, ?)",
                        (user_id, question_id, answer)
                    )
                # Если ответ - число (ID опции), сохраняем как option_id
                elif isinstance(answer, int):
                    await db.execute(
                        "INSERT INTO user_answers (user_id, question_id, option_id) VALUES (?, ?, ?)",
                        (user_id, question_id, answer)
                    )
            
            await db.commit()
            railway_print(f"Сохранены ответы на опрос для пользователя {user_id}", "INFO")
            return True
    except Exception as e:
        railway_print(f"Ошибка при сохранении ответов на опрос: {e}", "ERROR")
        logger.error(f"Ошибка при сохранении ответов на опрос: {e}")
        return False

async def get_user_answers(user_id: int) -> Dict[int, Union[str, int]]:
    """
    Получает ответы пользователя на опрос из базы данных
    
    Args:
        user_id: ID пользователя в Telegram
    
    Returns:
        Dict[int, Union[str, int]]: Словарь с ответами {question_id: answer}
    """
    answers = {}
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT question_id, option_id, answer_text FROM user_answers WHERE user_id = ?", 
                (user_id,)
            ) as cursor:
                async for row in cursor:
                    question_id = row['question_id']
                    # Если есть option_id, сохраняем его
                    if row['option_id'] is not None:
                        answers[question_id] = row['option_id']
                    # Иначе сохраняем текстовый ответ
                    else:
                        answers[question_id] = row['answer_text']
            
            return answers
    except Exception as e:
        railway_print(f"Ошибка при получении ответов пользователя: {e}", "ERROR")
        logger.error(f"Ошибка при получении ответов пользователя: {e}")
        return {}

async def save_user_state(user_id: int, state_name: str, state_data: Dict[str, Any]) -> bool:
    """
    Сохраняет состояние пользователя в базу данных (для сохранения данных FSM)
    
    Args:
        user_id: ID пользователя в Telegram
        state_name: Имя состояния
        state_data: Данные состояния
    
    Returns:
        bool: True, если операция успешна, False в противном случае
    """
    try:
        # Преобразуем данные состояния в строку
        import json
        state_json = json.dumps(state_data, ensure_ascii=False)
        
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем, существует ли таблица user_states
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_states (
                    user_id INTEGER PRIMARY KEY,
                    state_name TEXT,
                    state_data TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            
            # Проверяем, существует ли запись для данного пользователя
            async with db.execute(
                "SELECT user_id FROM user_states WHERE user_id = ?", 
                (user_id,)
            ) as cursor:
                user_exists = await cursor.fetchone()
            
            if user_exists:
                # Обновляем состояние пользователя
                await db.execute(
                    "UPDATE user_states SET state_name = ?, state_data = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (state_name, state_json, user_id)
                )
            else:
                # Добавляем новое состояние пользователя
                await db.execute(
                    "INSERT INTO user_states (user_id, state_name, state_data) VALUES (?, ?, ?)",
                    (user_id, state_name, state_json)
                )
            
            await db.commit()
            return True
    except Exception as e:
        railway_print(f"Ошибка при сохранении состояния пользователя: {e}", "ERROR")
        logger.error(f"Ошибка при сохранении состояния пользователя: {e}")
        return False

async def get_user_state(user_id: int) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Получает состояние пользователя из базы данных
    
    Args:
        user_id: ID пользователя в Telegram
    
    Returns:
        Tuple[Optional[str], Optional[Dict[str, Any]]]: Кортеж (имя состояния, данные состояния)
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Проверяем, существует ли таблица user_states
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_states (
                    user_id INTEGER PRIMARY KEY,
                    state_name TEXT,
                    state_data TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            
            async with db.execute(
                "SELECT state_name, state_data FROM user_states WHERE user_id = ?", 
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
            
            if row:
                import json
                state_name = row['state_name']
                state_data = json.loads(row['state_data'])
                return state_name, state_data
            return None, None
    except Exception as e:
        railway_print(f"Ошибка при получении состояния пользователя: {e}", "ERROR")
        logger.error(f"Ошибка при получении состояния пользователя: {e}")
        return None, None

async def clear_user_state(user_id: int) -> bool:
    """
    Очищает состояние пользователя в базе данных
    
    Args:
        user_id: ID пользователя в Telegram
    
    Returns:
        bool: True, если операция успешна, False в противном случае
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем, существует ли таблица user_states
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_states (
                    user_id INTEGER PRIMARY KEY,
                    state_name TEXT,
                    state_data TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            
            # Удаляем состояние пользователя
            await db.execute(
                "DELETE FROM user_states WHERE user_id = ?", 
                (user_id,)
            )
            
            await db.commit()
            return True
    except Exception as e:
        railway_print(f"Ошибка при очистке состояния пользователя: {e}", "ERROR")
        logger.error(f"Ошибка при очистке состояния пользователя: {e}")
        return False

async def save_profile_data(user_id: int, profile_text: str, personality_type: str) -> bool:
    """
    Сохраняет данные профиля пользователя в базу данных
    
    Args:
        user_id: ID пользователя в Telegram
        profile_text: Текст профиля
        personality_type: Тип личности
    
    Returns:
        bool: True, если операция успешна, False в противном случае
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем, существует ли таблица user_profiles
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id INTEGER PRIMARY KEY,
                    profile_text TEXT,
                    personality_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            
            # Проверяем, существует ли запись для данного пользователя
            async with db.execute(
                "SELECT user_id FROM user_profiles WHERE user_id = ?", 
                (user_id,)
            ) as cursor:
                user_exists = await cursor.fetchone()
            
            if user_exists:
                # Обновляем профиль пользователя
                await db.execute(
                    "UPDATE user_profiles SET profile_text = ?, personality_type = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (profile_text, personality_type, user_id)
                )
            else:
                # Добавляем новый профиль пользователя
                await db.execute(
                    "INSERT INTO user_profiles (user_id, profile_text, personality_type) VALUES (?, ?, ?)",
                    (user_id, profile_text, personality_type)
                )
            
            await db.commit()
            railway_print(f"Сохранен профиль для пользователя {user_id}", "INFO")
            return True
    except Exception as e:
        railway_print(f"Ошибка при сохранении профиля пользователя: {e}", "ERROR")
        logger.error(f"Ошибка при сохранении профиля пользователя: {e}")
        return False

async def get_profile_data(user_id: int) -> Tuple[Optional[str], Optional[str]]:
    """
    Получает данные профиля пользователя из базы данных
    
    Args:
        user_id: ID пользователя в Telegram
    
    Returns:
        Tuple[Optional[str], Optional[str]]: Кортеж (текст профиля, тип личности)
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Проверяем, существует ли таблица user_profiles
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id INTEGER PRIMARY KEY,
                    profile_text TEXT,
                    personality_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            
            async with db.execute(
                "SELECT profile_text, personality_type FROM user_profiles WHERE user_id = ?", 
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
            
            if row:
                return row['profile_text'], row['personality_type']
            return None, None
    except Exception as e:
        railway_print(f"Ошибка при получении профиля пользователя: {e}", "ERROR")
        logger.error(f"Ошибка при получении профиля пользователя: {e}")
        return None, None 