import logging
import os
import asyncio
from typing import Dict, Any, Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile

from button_states import MeditationStates

# Импортируем generate_audio из services.tts с обработкой ошибок
try:
    from services.tts import generate_audio
except ImportError:
    # Создаем заглушку для generate_audio если импорт не удался
    logger = logging.getLogger(__name__)
    logger.warning("Не удалось импортировать generate_audio из services.tts. Используем заглушку.")
    
    async def generate_audio(text: str, user_id: int, meditation_type: str = "default") -> tuple:
        """
        Заглушка для generate_audio.
        
        Args:
            text: Текст для преобразования в аудио
            user_id: ID пользователя Telegram
            meditation_type: Тип медитации
            
        Returns:
            tuple: (None, "Функция недоступна")
        """
        # Создаем директорию tmp, если она не существует
        os.makedirs("tmp", exist_ok=True)
        
        # Создаем пустой файл как заглушку
        file_name = f"placeholder_{meditation_type}_{user_id}.mp3"
        file_path = os.path.join("tmp", file_name)
        
        with open(file_path, "w") as f:
            f.write("# Placeholder audio file")
        
        return file_path, None

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем роутер для обработки медитаций
meditation_router = Router()

# Тексты медитаций
MEDITATION_TEXTS = {
    "relax": """Начните с того, что сядьте удобно и закройте глаза. 

Сделайте глубокий вдох через нос... задержите дыхание на мгновение... и медленно выдохните через рот.

Еще раз... вдох... и выдох...

Почувствуйте, как с каждым выдохом ваше тело становится все более расслабленным. 

Представьте, что с каждым вдохом вы наполняетесь спокойствием и умиротворением, а с каждым выдохом освобождаетесь от напряжения и стресса.

Направьте внимание на свои ступни. Почувствуйте, как они становятся тяжелыми и расслабленными.

Постепенно поднимайтесь выше... расслабляя голени... колени... бедра...

Позвольте расслаблению распространиться по всему вашему телу... по животу... груди... спине...

Ваши плечи опускаются, шея расслабляется... лицо становится спокойным и умиротворенным.

Сейчас вы находитесь в состоянии глубокого расслабления. Просто наблюдайте за своим дыханием... за тем, как воздух входит и выходит...

Дайте себе несколько минут побыть в этом состоянии покоя и гармонии.

Когда вы будете готовы вернуться, медленно начните шевелить пальцами рук и ног... сделайте глубокий вдох... и открывайте глаза...

Вы чувствуете себя отдохнувшим, расслабленным и умиротворенным.
""",

    "focus": """Найдите удобное положение и выпрямите спину. Вы можете сидеть на стуле или на полу — главное, чтобы вам было комфортно.

Закройте глаза и сделайте несколько глубоких вдохов и выдохов...

Сосредоточьте внимание на своем дыхании... на том, как воздух входит и выходит...

Если вы заметили, что ваши мысли где-то блуждают — это нормально. Просто мягко верните внимание к дыханию.

Теперь начните считать каждый вдох и выдох. Вдох — раз, выдох — два, вдох — три, и так до десяти. Затем начните сначала.

Если вы сбились со счета или отвлеклись — ничего страшного. Просто начните снова с единицы.

Продолжайте считать дыхание, сохраняя полное присутствие в настоящем моменте.

Если вам трудно сосредоточиться, представьте, что каждый вдох наполняет вас энергией и ясностью, а каждый выдох освобождает от отвлекающих мыслей.

Ваш разум становится все более сфокусированным и ясным с каждым дыханием.

Оставайтесь в этом состоянии сосредоточенности в течение нескольких минут...

Когда будете готовы, сделайте глубокий вдох, медленно откройте глаза и перенесите это чувство ясности и фокуса в свой день.
""",

    "sleep": """Лягте удобно в вашей кровати. Почувствуйте, как ваше тело погружается в матрас.

Сделайте глубокий вдох через нос... и медленный выдох через рот... 

Повторите еще раз... глубокий вдох... и медленный выдох...

С каждым выдохом вы погружаетесь в состояние глубокого расслабления и покоя.

Начните с пальцев ног. Почувствуйте, как они становятся тяжелыми и теплыми... Расслабление поднимается по вашим ногам... по коленям... бедрам...

Ваш живот поднимается и опускается в спокойном ритме дыхания... Грудь расслабляется... Спина отдыхает...

Ваши плечи становятся тяжелыми и опускаются... Руки полностью расслаблены от плеч до кончиков пальцев...

Шея и голова отдыхают... Лицо становится спокойным... Челюсть расслабляется... Лоб разглаживается...

Представьте, что вы находитесь в безопасном, тихом месте, где ничто не может вас побеспокоить. Это может быть пляж, лес, гора — любое место, где вы чувствуете себя спокойно и защищенно.

С каждым вдохом вы погружаетесь все глубже в сон... Каждый выдох уносит вас дальше от забот дня...

Ваше тело полностью расслаблено... Ваш разум спокоен и умиротворен...

Вы медленно дрейфуете в сторону сна... спокойного, глубокого, восстанавливающего сна...

Отпустите все мысли... отпустите день... отпустите все...

Позвольте себе мягко погрузиться в сон...
"""
}

# Функция для создания клавиатуры медитаций
def get_meditation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Разные типы медитаций
    builder.button(text="🧘 Медитация для расслабления", callback_data="meditate_relax")
    builder.button(text="🧠 Медитация для фокусировки", callback_data="meditate_focus")
    builder.button(text="😴 Медитация для сна", callback_data="meditate_sleep")
    builder.button(text="ℹ️ Справка по медитациям", callback_data="meditate_help")
    builder.button(text="◀️ Назад в меню", callback_data="main_menu")
    
    # Размещаем кнопки в столбик
    builder.adjust(1)
    
    return builder.as_markup()

# Обработчики команд
@meditation_router.message(Command("meditate"))
@meditation_router.message(F.text == "🧘 Медитации")
async def cmd_meditate(message: Message, state: FSMContext):
    """
    Обработчик команды /meditate и кнопки "Медитации".
    """
    await message.answer(
        "🧘 <b>Медитации и практики</b>\n\n"
        "Выберите тип медитации, и я подготовлю для вас голосовую инструкцию. "
        "Вы можете слушать её в любое удобное время.",
        reply_markup=get_meditation_keyboard(),
        parse_mode="HTML"
    )
    
    # Устанавливаем состояние выбора типа медитации
    await state.set_state(MeditationStates.selecting_type)

# Обработчики для инлайн-кнопок медитаций
@meditation_router.callback_query(F.data == "meditate_relax")
async def get_relax_meditation(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик запроса на медитацию для расслабления.
    """
    await callback.answer("Подготавливаю медитацию для расслабления...")
    
    # Отправляем текст медитации
    await callback.message.edit_text(
        "🧘 <b>Медитация для расслабления:</b>\n\n"
        "Сейчас вы получите голосовую медитацию. Найдите удобное место, "
        "где вас не будут беспокоить в течение 5-10 минут.",
        reply_markup=get_meditation_keyboard(),
        parse_mode="HTML"
    )
    
    try:
        # Отправляем сообщение о том, что медитация готовится
        preparing_message = await callback.message.answer(
            "⏳ Генерирую аудио медитацию...\n"
            "Это может занять несколько секунд."
        )
        
        # Генерируем аудио с помощью ElevenLabs API
        audio_path, error_reason = await generate_audio(
            text=MEDITATION_TEXTS["relax"],
            user_id=callback.from_user.id,
            meditation_type="relax"
        )
        
        # Удаляем сообщение о подготовке
        await preparing_message.delete()
        
        if audio_path:
            # Проверяем, что файл существует
            if os.path.exists(audio_path):
                try:
                    # Отправляем голосовое сообщение
                    await callback.message.answer_voice(
                        FSInputFile(audio_path),
                        caption="🧘 Медитация для расслабления. Сядьте удобно и следуйте инструкциям."
                    )
                    logger.info(f"Голосовое сообщение успешно отправлено пользователю {callback.from_user.id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке голосового сообщения: {e}")
                    # Если не удалось отправить голосовое, отправляем текст медитации
                    await callback.message.answer(
                        f"<b>Не удалось отправить аудио. Вот текст медитации:</b>\n\n{MEDITATION_TEXTS['relax']}",
                        parse_mode="HTML"
                    )
            else:
                logger.error(f"Файл {audio_path} не существует")
                await callback.message.answer(
                    f"<b>Не удалось создать аудио-файл. Вот текст медитации:</b>\n\n{MEDITATION_TEXTS['relax']}",
                    parse_mode="HTML"
                )
            
            # Удаляем временный файл
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                    logger.info(f"Временный файл {audio_path} удален")
            except Exception as e:
                logger.error(f"Ошибка при удалении временного файла: {e}")
        else:
            # Обрабатываем различные причины ошибок
            if error_reason == "quota_exceeded":
                await callback.message.answer(
                    "⚠️ <b>Превышен лимит генерации аудио</b>\n\n"
                    "К сожалению, достигнут ежедневный лимит генерации аудио. "
                    "Ниже приведен текст медитации, который вы можете прочитать самостоятельно.\n\n"
                    f"{MEDITATION_TEXTS['relax']}",
                    parse_mode="HTML"
                )
                logger.info(f"Пользователь {callback.from_user.id} получил текст медитации из-за превышения квоты")
            else:
                await callback.message.answer(
                    f"<b>Не удалось создать аудио-медитацию: {error_reason}</b>\n\n"
                    f"Вот текст медитации, который вы можете прочитать самостоятельно:\n\n{MEDITATION_TEXTS['relax']}",
                    parse_mode="HTML"
                )
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на медитацию: {e}")
        await callback.message.answer(
            "Произошла ошибка при подготовке медитации. Пожалуйста, повторите запрос позже."
        )
    
    # Сохраняем информацию о выполненной медитации
    logger.info(f"Пользователь {callback.from_user.id} получил медитацию для расслабления")

@meditation_router.callback_query(F.data == "meditate_focus")
async def get_focus_meditation(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик запроса на медитацию для фокусировки.
    """
    await callback.answer("Подготавливаю медитацию для фокусировки...")
    
    # Отправляем текст медитации
    await callback.message.edit_text(
        "🧠 <b>Медитация для фокусировки:</b>\n\n"
        "Сейчас вы получите голосовую медитацию. Найдите удобное место, "
        "где вас не будут беспокоить в течение 5-10 минут.",
        reply_markup=get_meditation_keyboard(),
        parse_mode="HTML"
    )
    
    try:
        # Отправляем сообщение о том, что медитация готовится
        preparing_message = await callback.message.answer(
            "⏳ Генерирую аудио медитацию...\n"
            "Это может занять несколько секунд."
        )
        
        # Генерируем аудио с помощью ElevenLabs API
        audio_path, error_reason = await generate_audio(
            text=MEDITATION_TEXTS["focus"],
            user_id=callback.from_user.id,
            meditation_type="focus"
        )
        
        # Удаляем сообщение о подготовке
        await preparing_message.delete()
        
        if audio_path:
            # Проверяем, что файл существует
            if os.path.exists(audio_path):
                try:
                    # Отправляем голосовое сообщение
                    await callback.message.answer_voice(
                        FSInputFile(audio_path),
                        caption="🧠 Медитация для фокусировки. Сядьте в удобной позе и следуйте инструкциям."
                    )
                    logger.info(f"Голосовое сообщение успешно отправлено пользователю {callback.from_user.id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке голосового сообщения: {e}")
                    # Если не удалось отправить голосовое, отправляем текст медитации
                    await callback.message.answer(
                        f"<b>Не удалось отправить аудио. Вот текст медитации:</b>\n\n{MEDITATION_TEXTS['focus']}",
                        parse_mode="HTML"
                    )
            else:
                logger.error(f"Файл {audio_path} не существует")
                await callback.message.answer(
                    f"<b>Не удалось создать аудио-файл. Вот текст медитации:</b>\n\n{MEDITATION_TEXTS['focus']}",
                    parse_mode="HTML"
                )
            
            # Удаляем временный файл
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                    logger.info(f"Временный файл {audio_path} удален")
            except Exception as e:
                logger.error(f"Ошибка при удалении временного файла: {e}")
        else:
            # Обрабатываем различные причины ошибок
            if error_reason == "quota_exceeded":
                await callback.message.answer(
                    "⚠️ <b>Превышен лимит генерации аудио</b>\n\n"
                    "К сожалению, достигнут ежедневный лимит генерации аудио. "
                    "Ниже приведен текст медитации, который вы можете прочитать самостоятельно.\n\n"
                    f"{MEDITATION_TEXTS['focus']}",
                    parse_mode="HTML"
                )
                logger.info(f"Пользователь {callback.from_user.id} получил текст медитации из-за превышения квоты")
            else:
                await callback.message.answer(
                    f"<b>Не удалось создать аудио-медитацию: {error_reason}</b>\n\n"
                    f"Вот текст медитации, который вы можете прочитать самостоятельно:\n\n{MEDITATION_TEXTS['focus']}",
                    parse_mode="HTML"
                )
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на медитацию: {e}")
        await callback.message.answer(
            "Произошла ошибка при подготовке медитации. Пожалуйста, повторите запрос позже."
        )
    
    # Сохраняем информацию о выполненной медитации
    logger.info(f"Пользователь {callback.from_user.id} получил медитацию для фокусировки")

@meditation_router.callback_query(F.data == "meditate_sleep")
async def get_sleep_meditation(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик запроса на медитацию для сна.
    """
    await callback.answer("Подготавливаю медитацию для сна...")
    
    # Отправляем текст медитации
    await callback.message.edit_text(
        "😴 <b>Медитация для сна:</b>\n\n"
        "Сейчас вы получите голосовую медитацию. Рекомендуется слушать "
        "ее лежа в кровати перед сном.",
        reply_markup=get_meditation_keyboard(),
        parse_mode="HTML"
    )
    
    try:
        # Отправляем сообщение о том, что медитация готовится
        preparing_message = await callback.message.answer(
            "⏳ Генерирую аудио медитацию...\n"
            "Это может занять несколько секунд."
        )
        
        # Генерируем аудио с помощью ElevenLabs API
        audio_path, error_reason = await generate_audio(
            text=MEDITATION_TEXTS["sleep"],
            user_id=callback.from_user.id,
            meditation_type="sleep"
        )
        
        # Удаляем сообщение о подготовке
        await preparing_message.delete()
        
        if audio_path:
            # Проверяем, что файл существует
            if os.path.exists(audio_path):
                try:
                    # Отправляем голосовое сообщение
                    await callback.message.answer_voice(
                        FSInputFile(audio_path),
                        caption="😴 Медитация для сна. Лягте удобно и следуйте инструкциям."
                    )
                    logger.info(f"Голосовое сообщение успешно отправлено пользователю {callback.from_user.id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке голосового сообщения: {e}")
                    # Если не удалось отправить голосовое, отправляем текст медитации
                    await callback.message.answer(
                        f"<b>Не удалось отправить аудио. Вот текст медитации:</b>\n\n{MEDITATION_TEXTS['sleep']}",
                        parse_mode="HTML"
                    )
            else:
                logger.error(f"Файл {audio_path} не существует")
                await callback.message.answer(
                    f"<b>Не удалось создать аудио-файл. Вот текст медитации:</b>\n\n{MEDITATION_TEXTS['sleep']}",
                    parse_mode="HTML"
                )
            
            # Удаляем временный файл
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                    logger.info(f"Временный файл {audio_path} удален")
            except Exception as e:
                logger.error(f"Ошибка при удалении временного файла: {e}")
        else:
            # Обрабатываем различные причины ошибок
            if error_reason == "quota_exceeded":
                await callback.message.answer(
                    "⚠️ <b>Превышен лимит генерации аудио</b>\n\n"
                    "К сожалению, достигнут ежедневный лимит генерации аудио. "
                    "Ниже приведен текст медитации, который вы можете прочитать самостоятельно.\n\n"
                    f"{MEDITATION_TEXTS['sleep']}",
                    parse_mode="HTML"
                )
                logger.info(f"Пользователь {callback.from_user.id} получил текст медитации из-за превышения квоты")
            else:
                await callback.message.answer(
                    f"<b>Не удалось создать аудио-медитацию: {error_reason}</b>\n\n"
                    f"Вот текст медитации, который вы можете прочитать самостоятельно:\n\n{MEDITATION_TEXTS['sleep']}",
                    parse_mode="HTML"
                )
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на медитацию: {e}")
        await callback.message.answer(
            "Произошла ошибка при подготовке медитации. Пожалуйста, повторите запрос позже."
        )
    
    # Сохраняем информацию о выполненной медитации
    logger.info(f"Пользователь {callback.from_user.id} получил медитацию для сна")

@meditation_router.callback_query(F.data == "meditate_help")
async def meditation_help(callback: CallbackQuery):
    """
    Обработчик запроса справки по медитациям.
    """
    await callback.answer("Отображаю справку по медитациям...")
    
    await callback.message.edit_text(
        "ℹ️ <b>Справка по медитациям:</b>\n\n"
        "Медитация — это практика целенаправленного внимания, которая помогает успокоить ум, "
        "снизить стресс и улучшить самочувствие.\n\n"
        "<b>Доступные типы медитаций:</b>\n\n"
        "• <b>Медитация для расслабления</b> — помогает снять напряжение и расслабиться\n"
        "• <b>Медитация для фокусировки</b> — улучшает концентрацию и ясность мышления\n"
        "• <b>Медитация для сна</b> — помогает успокоить ум и легче заснуть\n\n"
        "<b>Рекомендации:</b>\n"
        "• Найдите спокойное место, где вас не будут беспокоить\n"
        "• Убедитесь, что вам комфортно и удобно\n"
        "• Старайтесь практиковать медитацию регулярно для лучших результатов",
        reply_markup=get_meditation_keyboard(),
        parse_mode="HTML"
    )
    
    logger.info(f"Пользователь {callback.from_user.id} запросил справку по медитациям")

@meditation_router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик возврата в главное меню.
    """
    await callback.answer("Возвращаемся в главное меню...")
    
    # Сбрасываем состояние
    await state.clear()
    
    # Отправляем сообщение с главным меню
    await callback.message.edit_text(
        "👋 <b>Главное меню</b>\n\n"
        "Выберите, что вы хотите сделать:",
        reply_markup=InlineKeyboardBuilder().button(
            text="📝 Опрос", callback_data="start_survey"
        ).button(
            text="🧘 Медитации", callback_data="meditations"
        ).button(
            text="⏰ Напоминания", callback_data="reminders"
        ).button(
            text="👤 Профиль", callback_data="show_profile"
        ).button(
            text="💬 Помощь", callback_data="help"
        ).adjust(2, 2, 1).as_markup(),
        parse_mode="HTML"
    )
    
    logger.info(f"Пользователь {callback.from_user.id} вернулся в главное меню") 