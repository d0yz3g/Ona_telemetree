import logging
from typing import Dict, Any, Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Импортируем состояния для опроса
from button_states import SurveyStates

# Пытаемся импортировать модуль communication_handler
try:
    from communication_handler import generate_personalized_response, get_personality_type_from_profile, communication_handler_router
except ImportError:
    # Если не удалось импортировать, создаем заглушку
    logging.warning("Не удалось импортировать communication_handler_router, используется заглушка")
    from aiogram import Router
    communication_handler_router = Router(name="communication_handler")

from services.profile_analysis import analyze_profile

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем роутер для обработки обычных текстовых сообщений
conversation_router = Router(name="conversation")

# Ключевые фразы для распознавания запросов о профиле
PROFILE_QUERY_KEYWORDS = [
    "расскажи обо мне", "что ты знаешь обо мне", "мой профиль", "моя личность",
    "мои особенности", "мой характер", "какой я", "кто я", "мои сильные стороны",
    "мои слабые стороны", "мои способности", "что ты можешь сказать обо мне",
    "что говорит обо мне опрос", "расскажи о моем профиле", "анализ моего профиля",
    "исходя из опроса", "исходя из профиля", "что я за человек"
]

def is_profile_query(text: str) -> bool:
    """
    Проверяет, является ли сообщение запросом о профиле.
    
    Args:
        text: Текст сообщения
        
    Returns:
        bool: True, если это запрос о профиле, иначе False
    """
    text_lower = text.lower()
    for keyword in PROFILE_QUERY_KEYWORDS:
        if keyword in text_lower:
            return True
    return False

@conversation_router.message(F.text)
async def handle_text_message(message: Message, state: FSMContext):
    """
    Обрабатывает обычные текстовые сообщения от пользователя.
    
    Args:
        message: Сообщение от пользователя
        state: Состояние FSM
    """
    # Получаем текущее состояние пользователя
    current_state = await state.get_state()
    
    # Если пользователь находится в процессе прохождения опроса, 
    # не обрабатываем сообщение здесь, это будет сделано в survey_handler
    if current_state == SurveyStates.answering_questions:
        return
    
    # Игнорируем команды и специальные кнопки
    if message.text.startswith("/") or message.text in [
        "📝 Опрос", "👤 Профиль", "🧘 Медитации", 
        "⏰ Напоминания", "💬 Помощь", "🔄 Рестарт", 
        "❌ Отменить", "❌ Отменить опрос"
    ]:
        return
    
    # Показываем индикатор "печатает..."
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Получаем данные пользователя из состояния
    user_data = await state.get_data()
    
    # Проверяем, есть ли у пользователя профиль
    if user_data.get("profile_completed", False):
        # Получаем тип личности
        personality_type = user_data.get("personality_type", None)
        profile_text = user_data.get("profile_text", "")
        
        # Если тип личности не указан явно, определяем его из текста профиля
        if not personality_type and profile_text:
            personality_type = await get_personality_type_from_profile(profile_text)
            # Сохраняем тип личности в состоянии
            await state.update_data(personality_type=personality_type)
        
        # Создаем словарь с профилем пользователя
        user_profile = {
            "personality_type": personality_type or "Интеллектуальный",
            "profile_text": profile_text
        }
        
        # Получаем историю переписки (если есть)
        conversation_history = user_data.get("conversation_history", [])
        
        try:
            # Формируем инструкцию для генерации ответа на основе правил из rules2.0
            interactive_prompt = f"""
            Я психолог-консультант, следующий принципам поэтично-лирического стиля общения.
            
            Правила общения:
            1. Поэтично-лирический стиль с лёгким футуристическим юмором и яркими метафорами.
            2. Полная честность без лести и преувеличений.
            3. В темах науки, бизнеса или нейро-биохакинга – чёткая, лаконичная, научно-обоснованная проза.
            4. Разговорный и интерактивный тон (ментор и со-творец, не лектор).
            
            Структура ответа:
            - Начинай с короткого, тёплого обращения.
            - Используй неформальное обращение на "ты".
            - Разделяй блоки символом ⸻ для создания визуальной паузы.
            - Задавай личные вопросы, углубляющие мотивы и смыслы.
            - После раскрытия темы предлагай три варианта "куда дальше".
            - Используй короткие абзацы (1-3 предложения).
            - Подчеркивай творческую автономию и свободу выбора собеседника.
            
            Баланс в ответе:
            - 60% конкретные идеи и рекомендации
            - 30% поэтичные метафоры и образы
            - 10% глубокие вопросы для размышления
            
            ВАЖНО: На каждый запрос генерируй УНИКАЛЬНЫЙ ответ, а не используй шаблоны.
            ВАЖНО: Всегда отвечай на конкретный вопрос пользователя.
            
            Запрос пользователя: {message.text}
            Тип личности пользователя: {personality_type}
            """
            
            # Проверяем, является ли сообщение запросом о профиле
            if is_profile_query(message.text):
                # Если это запрос о профиле, используем специализированный анализ
                response = await analyze_profile(user_profile, message.text)
                logger.info(f"Выполнен анализ профиля для пользователя {message.from_user.id}")
            else:
                # Иначе генерируем персонализированный ответ с учетом новых правил
                response = await generate_personalized_response(
                    message.text, 
                    user_profile, 
                    conversation_history,
                    additional_instructions=interactive_prompt
                )
            
            # Резюмируем сообщение пользователя (<30 слов) для сохранения контекста
            user_message_summary = message.text[:150] + "..." if len(message.text) > 150 else message.text
            
            # Обновляем историю переписки
            conversation_history.append({"role": "user", "content": user_message_summary})
            conversation_history.append({"role": "assistant", "content": response})
            
            # Обрезаем историю переписки, чтобы она не была слишком длинной
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]
            
            # Обновляем состояние
            await state.update_data(conversation_history=conversation_history)
            
            # Отправляем ответ
            await message.answer(response)
            
            logger.info(f"Отправлен персонализированный ответ пользователю {message.from_user.id} (тип: {personality_type})")
            
        except Exception as e:
            logger.error(f"Ошибка при генерации персонализированного ответа: {e}")
            # Проверяем, связана ли ошибка с отсутствием API ключа
            if "OPENAI_API_KEY" in str(e) or "authentication" in str(e).lower() or "api key" in str(e).lower():
                await message.answer(
                    "Здравствуй, искатель знаний!\n\n"
                    "К сожалению, сейчас я не могу сгенерировать персонализированный ответ из-за проблем с API ключом.\n\n"
                    "⸻\n\n"
                    "Для администратора: Пожалуйста, проверьте настройки OPENAI_API_KEY в файле .env\n\n"
                    "Что ты хочешь сделать дальше?\n"
                    "- Задать другой вопрос?\n"
                    "- Перезапустить бота командой /restart?\n"
                    "- Обратиться к администратору?"
                )
            else:
                # Отправляем общий ответ в случае ошибки
                await message.answer(
                    "Здравствуй, исследователь глубин!\n\n"
                    "Произошла ошибка при обработке твоего сообщения. Пожалуйста, повтори попытку позже или попробуй перезапустить бота.\n\n"
                    "⸻\n\n"
                    "Что ты хочешь сделать дальше?\n"
                    "- Повторить вопрос?\n"
                    "- Перезапустить бота командой /restart?\n"
                    "- Спросить что-то другое?"
                )
    else:
        # Если профиля нет, предлагаем пройти опрос
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Начать опрос", callback_data="start_survey")
        
        await message.answer(
            "Чтобы получить более персонализированные ответы, рекомендую пройти опрос и создать ваш психологический профиль. "
            "Это позволит мне лучше понять ваши особенности и адаптировать свои ответы под ваш стиль мышления.",
            reply_markup=builder.as_markup()
        )

@conversation_router.callback_query(F.data == "start_survey")
async def start_survey_from_callback(callback: CallbackQuery, state: FSMContext):
    """
    Запускает опрос из callback-кнопки.
    
    Args:
        callback: Callback query
        state: Состояние FSM
    """
    # Импортируем функцию запуска опроса
    from survey_handler import start_survey
    
    # Запускаем опрос
    await start_survey(callback.message, state)
    
    # Отвечаем на callback
    await callback.answer("Начинаем опрос")

@conversation_router.message(Command("profile"))
@conversation_router.message(F.text == "👤 Профиль")
async def show_profile(message: Message, state: FSMContext):
    """
    Отображает психологический профиль пользователя.
    
    Args:
        message: Сообщение от пользователя
        state: Состояние FSM
    """
    # Получаем данные пользователя из состояния
    user_data = await state.get_data()
    
    # Проверяем, есть ли у пользователя профиль
    if user_data.get("profile_completed", False):
        profile_text = user_data.get("profile_text", "")
        
        # Отправляем профиль
        await message.answer(
            f"<b>Ваш психологический профиль:</b>\n\n"
            f"{profile_text}",
            parse_mode="HTML"
        )
    else:
        # Если профиля нет, предлагаем пройти опрос
        await message.answer(
            "У вас пока нет психологического профиля. Хотите пройти опрос сейчас?",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "✅ Да, начать опрос", "callback_data": "start_survey"}],
                    [{"text": "❌ Нет, позже", "callback_data": "cancel_survey"}]
                ]
            }
        ) 