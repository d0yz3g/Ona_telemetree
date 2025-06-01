import logging
import os
import tempfile
from typing import Optional, Dict, Any
from aiogram import Router, F
from aiogram.types import Message, Voice, FSInputFile
from aiogram.fsm.context import FSMContext

from services.stt import transcribe_voice

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем роутер для обработки голосовых сообщений
voice_router = Router()

# Проверка наличия необходимого API-ключа для распознавания голоса
WHISPER_API_KEY = os.getenv("OPENAI_API_KEY")
if not WHISPER_API_KEY:
    logger.warning("OPENAI_API_KEY не найден в переменных окружения. Функция распознавания голоса будет недоступна.")

@voice_router.message(F.voice)
async def handle_voice_message(message: Message, state: FSMContext):
    """
    Обрабатывает голосовые сообщения от пользователя.
    
    Args:
        message: Голосовое сообщение от пользователя
        state: Состояние FSM
    """
    # Показываем индикатор "записывает аудио" для начальной обработки
    await message.bot.send_chat_action(chat_id=message.chat.id, action="record_voice")
    
    # Сообщаем пользователю, что начинаем обработку голосового сообщения
    process_message = await message.answer("🎙 Обрабатываю ваше голосовое сообщение...")
    
    try:
        # Получаем файл голосового сообщения
        voice: Voice = message.voice
        voice_file = await message.bot.get_file(voice.file_id)
        
        # Сохраняем файл во временный каталог
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
            file_path = temp_file.name
        
        await message.bot.download_file(voice_file.file_path, file_path)
        
        # Показываем индикатор "печатает..." пока обрабатываем аудио
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        
        # Транскрибируем голосовое сообщение в текст
        text = await transcribe_voice(file_path)
        
        # Удаляем временный файл
        os.unlink(file_path)
        
        # Если текст не распознан, сообщаем об ошибке
        if not text:
            await process_message.edit_text(
                "❌ Не удалось распознать голосовое сообщение. Пожалуйста, попробуйте еще раз или отправьте текстовое сообщение."
            )
            return
        
        # Удаляем сообщение о процессе обработки
        await process_message.delete()
        
        # Отправляем распознанный текст пользователю
        await message.answer(
            f"🔍 <b>Распознанный текст:</b>\n\n{text}",
            parse_mode="HTML"
        )
        
        # Получаем данные пользователя из состояния
        user_data = await state.get_data()
        
        # Проверяем, есть ли у пользователя профиль
        if user_data.get("profile_completed", False):
            # Показываем индикатор "печатает..." пока генерируем ответ
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
            
            # Импортируем функцию для генерации персонализированного ответа
            from communication_handler import generate_personalized_response
            
            # Создаем словарь с профилем пользователя
            user_profile = {
                "personality_type": user_data.get("personality_type", "Интеллектуальный"),
                "profile_text": user_data.get("profile_text", "")
            }
            
            # Получаем историю переписки (если есть)
            conversation_history = user_data.get("conversation_history", [])
            
            # Формируем инструкцию для генерации ответа на основе правил Interactive Personalisation Loop
            interactive_prompt = f"""
            Я психолог-консультант, следующий принципам Interactive Personalisation Loop:
            
            1. Детектирую и определяю суть запроса пользователя.
            2. Уточняю детали и контекст вопросами (если необходимо).
            3. Анализирую и раскрываю глубинные причины.
            4. Предлагаю ясный и простой алгоритм.
            5. Завершаю предложением до трёх вариантов дальнейших действий.
            
            Запрос пользователя (голосовое сообщение): {text}
            Тип личности пользователя: {user_profile["personality_type"]}
            
            Я должен учитывать психологический тип пользователя и его особенности.
            Мой ответ должен быть структурирован, конкретен и персонализирован.
            """
            
            # Генерируем персонализированный ответ с учетом новых правил и механизма сохранения диалога
            response = await generate_personalized_response(
                text, 
                user_profile, 
                conversation_history,
                additional_instructions=interactive_prompt,
                user_id=message.from_user.id  # Передаем ID пользователя для механизма сохранения диалога
            )
            
            # Резюмируем сообщение пользователя (<30 слов) для сохранения контекста
            user_message_summary = text[:150] + "..." if len(text) > 150 else text
            
            # Обновляем историю переписки для совместимости со старым механизмом
            conversation_history.append({"role": "user", "content": user_message_summary})
            conversation_history.append({"role": "assistant", "content": response})
            
            # Обрезаем историю переписки, чтобы она не была слишком длинной
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]
            
            # Обновляем состояние
            await state.update_data(conversation_history=conversation_history)
            
            # Отправляем ответ
            await message.answer(response)
            
            logger.info(f"Голосовое сообщение пользователя {message.from_user.id} успешно обработано")
        else:
            # Если профиля нет, предлагаем пройти опрос
            await message.answer(
                "Чтобы получить более персонализированные ответы, рекомендую пройти опрос и создать ваш психологический профиль. "
                "Это позволит мне лучше понять ваши особенности и адаптировать свои ответы под ваш стиль мышления."
            )
            
            # Предлагаем кнопку для начала опроса
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Начать опрос", callback_data="start_survey")
            
            await message.answer(
                "Хотите пройти опрос сейчас?",
                reply_markup=builder.as_markup()
            )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {e}")
        # Обновляем сообщение о процессе обработки
        await process_message.edit_text(
            "❌ Произошла ошибка при обработке голосового сообщения. Пожалуйста, попробуйте еще раз или отправьте текстовое сообщение."
        ) 