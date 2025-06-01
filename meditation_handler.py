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
from openai import AsyncOpenAI
import httpx

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

# Получаем OPENAI_API_KEY из переменных окружения
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY не найден в переменных окружения. Функция генерации медитаций будет работать в демо-режиме.")

# Инициализация клиента OpenAI с API-ключом из переменных окружения (если доступен)
http_client = httpx.AsyncClient()
client = None
if OPENAI_API_KEY:
    try:
        client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            http_client=http_client
        )
        logger.info("OpenAI API клиент успешно инициализирован в meditation_handler.py")
    except Exception as e:
        logger.error(f"Ошибка при инициализации OpenAI API: {e}")

# Константа максимального количества медитаций
MAX_MEDITATION_COUNT = 4

# Функция для обновления и проверки счетчика медитаций
async def update_meditation_count(state: FSMContext, user_id: int) -> bool:
    """
    Обновляет счетчик медитаций пользователя и проверяет, превышен ли лимит.
    
    Args:
        state: Контекст состояния FSM
        user_id: ID пользователя Telegram
        
    Returns:
        bool: True, если пользователь может получить медитацию, False если лимит превышен
    """
    # Получаем текущие данные пользователя
    user_data = await state.get_data()
    
    # Получаем текущий счетчик медитаций или устанавливаем 0, если счетчика нет
    meditation_count = user_data.get("user_meditation_count", 0)
    
    # Проверяем, превышен ли лимит
    if meditation_count >= MAX_MEDITATION_COUNT:
        logger.info(f"Пользователь {user_id} превысил лимит медитаций ({MAX_MEDITATION_COUNT})")
        return False
    
    # Увеличиваем счетчик и сохраняем его
    meditation_count += 1
    await state.update_data(user_meditation_count=meditation_count)
    logger.info(f"Обновлен счетчик медитаций для пользователя {user_id}: {meditation_count}")
    
    return True

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

# Функция для генерации персонализированной медитации на основе профиля пользователя
async def generate_personalized_meditation(user_profile: Dict[str, Any], duration: str = "short") -> str:
    """
    Генерирует персонализированную медитацию для пользователя на основе его психологического профиля.
    
    Args:
        user_profile: Профиль пользователя (включает тип личности и полный текст профиля)
        duration: Продолжительность медитации ('short', 'medium', 'long')
        
    Returns:
        str: Текст медитации
    """
    # Получаем тип личности и текст профиля
    personality_type = user_profile.get("personality_type", "Интеллектуальный")
    profile_text = user_profile.get("profile_text", "")
    
    # Определяем длительность в зависимости от параметра
    if duration == "short":
        duration_text = "2-3 минуты"
        length_guide = "150-200 слов"
    elif duration == "medium":
        duration_text = "5-7 минут"
        length_guide = "300-400 слов"
    else:  # long
        duration_text = "10-15 минут"
        length_guide = "600-800 слов"
    
    # Проверяем, доступен ли API клиент OpenAI
    use_fallback_meditation = not client
    
    # Если API недоступен или профиль не найден, используем заготовленные медитации
    if use_fallback_meditation or not profile_text:
        logger.warning(f"OpenAI API недоступен или профиль не найден. Используем заготовленную медитацию для типа {personality_type}")
        
        # Заготовленные базовые медитации
        basic_meditations = {
            "Интеллектуальный": f"""**Медитация для интеллектуального типа - {duration_text}**

Устройся удобно и позволь своему телу найти комфортное положение... Закрой глаза и сделай несколько глубоких вдохов...

Представь свой разум как бескрайнее звёздное небо... Каждая мысль - яркая звезда в этом пространстве... Наблюдай за ними с интересом и спокойствием исследователя...

Почувствуй, как с каждым вдохом ты наполняешься ясностью и спокойствием... С каждым выдохом отпускаешь напряжение и беспокойство...

Твой аналитический ум - твоя сила... Но сейчас позволь себе просто быть... Без анализа, без оценки... Только наблюдение за дыханием и ощущениями в теле...

Когда будешь готова, медленно вернись в комнату... Открой глаза, сохраняя это состояние внутренней тишины и ясности...""",
            
            "Эмоциональный": f"""**Медитация для эмоционального типа - {duration_text}**

Устройся удобно, найди положение, в котором твоё тело чувствует себя защищённым... Закрой глаза и сделай глубокий вдох...

Представь себя на берегу тёплого моря... Волны нежно омывают песок... Каждая волна - это эмоция, приходящая и уходящая естественным образом...

Почувствуй, как твоё сердце открывается навстречу этому ритму... Ты можешь просто наблюдать за своими чувствами, не отождествляясь с ними полностью...

Твоя эмоциональная глубина - твоя сила... Сейчас ты учишься быть в гармонии со своими чувствами... Наблюдая их, как наблюдаешь закат - с восхищением и принятием...

Когда будешь готова, медленно возвращайся в комнату... Открой глаза, сохраняя эту внутреннюю гармонию и спокойствие...""",
            
            "Творческий": f"""**Медитация для творческого типа - {duration_text}**

Найди удобное положение и позволь своему телу полностью расслабиться... Закрой глаза и сделай три глубоких вдоха...

Представь себя в центре прекрасного сада возможностей... Каждый цветок, каждое растение - проявление твоей творческой силы... Множество красок, форм и ароматов окружают тебя...

Почувствуй, как твоё воображение свободно течёт, создавая новые образы и идеи... С каждым вдохом ты наполняешься вдохновением, с каждым выдохом освобождаешь пространство для нового...

Твоя творческая сила - твой дар миру... Сейчас ты учишься доверять этому потоку, позволяя идеям приходить свободно и легко...

Когда будешь готова, медленно возвращайся в комнату... Открой глаза, сохраняя это чувство творческого изобилия и свободы...""",
            
            # Общая медитация по умолчанию
            "default": f"""**Медитация для расслабления и присутствия - {duration_text}**

Найди удобное положение и позволь своему телу полностью расслабиться... Закрой глаза и сделай три глубоких вдоха...

С каждым вдохом ты наполняешься спокойствием и силой... С каждым выдохом отпускаешь напряжение и усталость...

Почувствуй, как твоё тело становится тяжелее... Как растворяются все тревоги в пространстве вокруг тебя...

Ты в безопасности здесь и сейчас... Полностью присутствуешь в этом моменте... Позволь себе просто быть, без необходимости что-то делать или о чём-то думать...

Когда будешь готова, медленно возвращайся в комнату... Сохраняя это чувство покоя и присутствия... Открой глаза, оставаясь в контакте с внутренним спокойствием..."""
        }
        
        # Возвращаем базовую медитацию в зависимости от типа личности
        return basic_meditations.get(personality_type, basic_meditations["default"])
    
    try:
        # Подготовка системного промпта
        system_prompt = f"""Ты — поэтичный проводник по внутреннему миру проекта ONA. Создай медитацию для участницы на основе её психологического профиля. 

Твоя медитация должна быть глубоко личной — используй метафоры, образы и темы, отражающие её внутренние силы, архетип, импульсы и эмоциональную структуру из профиля. Обращайся на «ты», создавай текст, который звучит как голос близкого друга — мягкий, понимающий, вдохновляющий.

Структурируй медитацию в четыре этапа:
1. Вступление и расслабление (плавное погружение)
2. Основная практика (работа с вниманием)
3. Интеграция (соединение с внутренними ресурсами)
4. Завершение (возвращение к повседневности)

Говори размеренно, с естественными паузами (обозначенными многоточием). Используй музыкальность речи, мягкие интонации, повторы для усиления эффекта. Учитывай, что это медитация продолжительностью {duration_text}, так что текст должен быть длиной примерно {length_guide}.

Глубоко опирайся на содержание профиля, избегая общих фраз, которые могли бы подойти любому. Делай медитацию исключительно персонализированной.

Стиль: поэтичный, образный, с метафорами соответствующими типу личности из профиля. Тон: спокойный, мягкий, уверенный."""

        try:
            # Отправляем запрос в OpenAI
            response = await client.chat.completions.create(
                model="gpt-4o",
                temperature=0.7,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Вот психологический профиль пользователя:\n\n{profile_text}\n\nСоздай персонализированную медитацию для этого человека длительностью {duration_text} (примерно {length_guide})."}
                ]
            )
            
            # Получаем сгенерированную медитацию
            meditation_text = response.choices[0].message.content
            
            # Логируем результат
            logger.info(f"Сгенерирована персонализированная медитация длиной {len(meditation_text)} символов")
            
            return meditation_text
        except Exception as e:
            # Проверяем, связана ли ошибка с превышением квоты
            error_str = str(e)
            if "quota" in error_str.lower() or "insufficient_quota" in error_str or "429" in error_str:
                logger.error(f"Ошибка квоты OpenAI API при генерации медитации: {e}. Переключаемся на базовую медитацию.")
                use_fallback_meditation = True
            else:
                # Если ошибка другого типа, пробрасываем её дальше
                raise e
    
    except Exception as e:
        logger.error(f"Ошибка при генерации медитации: {e}")
        use_fallback_meditation = True
    
    # Если API недоступен или возникла ошибка квоты, используем заготовленную медитацию
    if use_fallback_meditation:
        # Заготовленные базовые медитации
        basic_meditations = {
            "Интеллектуальный": f"""**Медитация для интеллектуального типа - {duration_text}**

Устройся удобно и позволь своему телу найти комфортное положение... Закрой глаза и сделай несколько глубоких вдохов...

Представь свой разум как бескрайнее звёздное небо... Каждая мысль - яркая звезда в этом пространстве... Наблюдай за ними с интересом и спокойствием исследователя...

Почувствуй, как с каждым вдохом ты наполняешься ясностью и спокойствием... С каждым выдохом отпускаешь напряжение и беспокойство...

Твой аналитический ум - твоя сила... Но сейчас позволь себе просто быть... Без анализа, без оценки... Только наблюдение за дыханием и ощущениями в теле...

Когда будешь готова, медленно вернись в комнату... Открой глаза, сохраняя это состояние внутренней тишины и ясности...""",
            
            "Эмоциональный": f"""**Медитация для эмоционального типа - {duration_text}**

Устройся удобно, найди положение, в котором твоё тело чувствует себя защищённым... Закрой глаза и сделай глубокий вдох...

Представь себя на берегу тёплого моря... Волны нежно омывают песок... Каждая волна - это эмоция, приходящая и уходящая естественным образом...

Почувствуй, как твоё сердце открывается навстречу этому ритму... Ты можешь просто наблюдать за своими чувствами, не отождествляясь с ними полностью...

Твоя эмоциональная глубина - твоя сила... Сейчас ты учишься быть в гармонии со своими чувствами... Наблюдая их, как наблюдаешь закат - с восхищением и принятием...

Когда будешь готова, медленно возвращайся в комнату... Открой глаза, сохраняя эту внутреннюю гармонию и спокойствие...""",
            
            "Творческий": f"""**Медитация для творческого типа - {duration_text}**

Найди удобное положение и позволь своему телу полностью расслабиться... Закрой глаза и сделай три глубоких вдоха...

Представь себя в центре прекрасного сада возможностей... Каждый цветок, каждое растение - проявление твоей творческой силы... Множество красок, форм и ароматов окружают тебя...

Почувствуй, как твоё воображение свободно течёт, создавая новые образы и идеи... С каждым вдохом ты наполняешься вдохновением, с каждым выдохом освобождаешь пространство для нового...

Твоя творческая сила - твой дар миру... Сейчас ты учишься доверять этому потоку, позволяя идеям приходить свободно и легко...

Когда будешь готова, медленно возвращайся в комнату... Открой глаза, сохраняя это чувство творческого изобилия и свободы...""",
            
            # Общая медитация по умолчанию
            "default": f"""**Медитация для расслабления и присутствия - {duration_text}**

Найди удобное положение и позволь своему телу полностью расслабиться... Закрой глаза и сделай три глубоких вдоха...

С каждым вдохом ты наполняешься спокойствием и силой... С каждым выдохом отпускаешь напряжение и усталость...

Почувствуй, как твоё тело становится тяжелее... Как растворяются все тревоги в пространстве вокруг тебя...

Ты в безопасности здесь и сейчас... Полностью присутствуешь в этом моменте... Позволь себе просто быть, без необходимости что-то делать или о чём-то думать...

Когда будешь готова, медленно возвращайся в комнату... Сохраняя это чувство покоя и присутствия... Открой глаза, оставаясь в контакте с внутренним спокойствием..."""
        }
        
        # Возвращаем базовую медитацию в зависимости от типа личности
        return basic_meditations.get(personality_type, basic_meditations["default"])

# Обработчики для инлайн-кнопок медитаций
@meditation_router.callback_query(F.data == "meditate_relax")
async def get_relax_meditation(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик запроса на медитацию для расслабления.
    """
    await callback.answer("Подготавливаю медитацию для расслабления...")
    
    # Проверяем счетчик медитаций
    can_get_meditation = await update_meditation_count(state, callback.from_user.id)
    
    if not can_get_meditation:
        # Если лимит превышен, отправляем сообщение и выходим
        await callback.message.edit_text(
            "🧘 <b>Медитация для расслабления:</b>\n\n"
            "Ты уже получила 4 уникальные медитации. Если ты чувствуешь, что готова к новой — "
            "напиши нам отдельно, и мы обсудим.",
            reply_markup=get_meditation_keyboard(),
            parse_mode="HTML"
        )
        return
    
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
        
        # Получаем данные пользователя
        user_data = await state.get_data()
        profile_text = user_data.get("profile_text", "")
        user_name = user_data.get("name", "")
        
        # Генерируем персонализированную медитацию
        meditation_text = await generate_personalized_meditation(
            user_profile=user_data,
            duration="short"
        )
        
        # Генерируем аудио с помощью ElevenLabs API
        audio_path, error_reason = await generate_audio(
            text=meditation_text,
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
                        f"<b>Не удалось отправить аудио. Вот текст медитации:</b>\n\n{meditation_text}",
                        parse_mode="HTML"
                    )
            else:
                logger.error(f"Файл {audio_path} не существует")
                await callback.message.answer(
                    f"<b>Не удалось создать аудио-файл. Вот текст медитации:</b>\n\n{meditation_text}",
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
                    f"{meditation_text}",
                    parse_mode="HTML"
                )
                logger.info(f"Пользователь {callback.from_user.id} получил текст медитации из-за превышения квоты")
            else:
                await callback.message.answer(
                    f"<b>Не удалось создать аудио-медитацию: {error_reason}</b>\n\n"
                    f"Вот текст медитации, который вы можете прочитать самостоятельно:\n\n{meditation_text}",
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
    
    # Проверяем счетчик медитаций
    can_get_meditation = await update_meditation_count(state, callback.from_user.id)
    
    if not can_get_meditation:
        # Если лимит превышен, отправляем сообщение и выходим
        await callback.message.edit_text(
            "🧠 <b>Медитация для фокусировки:</b>\n\n"
            "Ты уже получила 4 уникальные медитации. Если ты чувствуешь, что готова к новой — "
            "напиши нам отдельно, и мы обсудим.",
            reply_markup=get_meditation_keyboard(),
            parse_mode="HTML"
        )
        return
    
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
        
        # Получаем данные пользователя
        user_data = await state.get_data()
        profile_text = user_data.get("profile_text", "")
        user_name = user_data.get("name", "")
        
        # Генерируем персонализированную медитацию
        meditation_text = await generate_personalized_meditation(
            user_profile=user_data,
            duration="short"
        )
        
        # Генерируем аудио с помощью ElevenLabs API
        audio_path, error_reason = await generate_audio(
            text=meditation_text,
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
                        caption="🧠 Медитация для фокусировки. Сядьте удобно и следуйте инструкциям."
                    )
                    logger.info(f"Голосовое сообщение успешно отправлено пользователю {callback.from_user.id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке голосового сообщения: {e}")
                    # Если не удалось отправить голосовое, отправляем текст медитации
                    await callback.message.answer(
                        f"<b>Не удалось отправить аудио. Вот текст медитации:</b>\n\n{meditation_text}",
                        parse_mode="HTML"
                    )
            else:
                logger.error(f"Файл {audio_path} не существует")
                await callback.message.answer(
                    f"<b>Не удалось создать аудио-файл. Вот текст медитации:</b>\n\n{meditation_text}",
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
                    f"{meditation_text}",
                    parse_mode="HTML"
                )
                logger.info(f"Пользователь {callback.from_user.id} получил текст медитации из-за превышения квоты")
            else:
                await callback.message.answer(
                    f"<b>Не удалось создать аудио-медитацию: {error_reason}</b>\n\n"
                    f"Вот текст медитации, который вы можете прочитать самостоятельно:\n\n{meditation_text}",
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
    
    # Проверяем счетчик медитаций
    can_get_meditation = await update_meditation_count(state, callback.from_user.id)
    
    if not can_get_meditation:
        # Если лимит превышен, отправляем сообщение и выходим
        await callback.message.edit_text(
            "😴 <b>Медитация для сна:</b>\n\n"
            "Ты уже получила 4 уникальные медитации. Если ты чувствуешь, что готова к новой — "
            "напиши нам отдельно, и мы обсудим.",
            reply_markup=get_meditation_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Отправляем текст медитации
    await callback.message.edit_text(
        "😴 <b>Медитация для сна:</b>\n\n"
        "Сейчас вы получите голосовую медитацию. Найдите удобное место, "
        "где вас не будут беспокоить в течение 10-15 минут.",
        reply_markup=get_meditation_keyboard(),
        parse_mode="HTML"
    )
    
    try:
        # Отправляем сообщение о том, что медитация готовится
        preparing_message = await callback.message.answer(
            "⏳ Генерирую аудио медитацию...\n"
            "Это может занять несколько секунд."
        )
        
        # Получаем данные пользователя
        user_data = await state.get_data()
        profile_text = user_data.get("profile_text", "")
        user_name = user_data.get("name", "")
        
        # Генерируем персонализированную медитацию
        meditation_text = await generate_personalized_meditation(
            user_profile=user_data,
            duration="medium"  # Для сна делаем немного длиннее
        )
        
        # Генерируем аудио с помощью ElevenLabs API
        audio_path, error_reason = await generate_audio(
            text=meditation_text,
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
                        caption="😴 Медитация для сна. Расположитесь удобно и следуйте инструкциям."
                    )
                    logger.info(f"Голосовое сообщение успешно отправлено пользователю {callback.from_user.id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке голосового сообщения: {e}")
                    # Если не удалось отправить голосовое, отправляем текст медитации
                    await callback.message.answer(
                        f"<b>Не удалось отправить аудио. Вот текст медитации:</b>\n\n{meditation_text}",
                        parse_mode="HTML"
                    )
            else:
                logger.error(f"Файл {audio_path} не существует")
                await callback.message.answer(
                    f"<b>Не удалось создать аудио-файл. Вот текст медитации:</b>\n\n{meditation_text}",
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
                    f"{meditation_text}",
                    parse_mode="HTML"
                )
                logger.info(f"Пользователь {callback.from_user.id} получил текст медитации из-за превышения квоты")
            else:
                await callback.message.answer(
                    f"<b>Не удалось создать аудио-медитацию: {error_reason}</b>\n\n"
                    f"Вот текст медитации, который вы можете прочитать самостоятельно:\n\n{meditation_text}",
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
    # Получаем текущее состояние пользователя
    current_state = await state.get_state()
    
    # Если пользователь находится в состоянии опроса или разговора, очищаем состояние
    if current_state == MeditationStates.selecting_type:
        await state.clear()
    
    # Проверяем, существует ли импортированная функция get_main_keyboard
    try:
        from survey_handler import get_main_keyboard
        
        # Отправляем сообщение с главной клавиатурой
        await callback.message.edit_text(
            "Возвращаемся в главное меню...",
            reply_markup=None
        )
        
        await callback.message.answer(
            "Выберите нужный раздел:",
            reply_markup=get_main_keyboard()
        )
        
    except ImportError:
        # Если не удалось импортировать get_main_keyboard, используем базовую клавиатуру
        from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
        
        basic_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📝 Опрос"), KeyboardButton(text="🧘 Медитации")],
                [KeyboardButton(text="💬 Помощь")]
            ],
            resize_keyboard=True
        )
        
        await callback.message.edit_text(
            "Возвращаемся в главное меню...",
            reply_markup=None
        )
        
        await callback.message.answer(
            "Выберите нужный раздел:",
            reply_markup=basic_keyboard
        )
    
    # Отвечаем на callback, чтобы убрать индикатор загрузки у кнопки
    await callback.answer()

# Добавляем обработчик для просмотра счетчика медитаций
@meditation_router.message(Command("meditation_count"))
async def cmd_meditation_count(message: Message, state: FSMContext):
    """
    Обработчик команды /meditation_count для просмотра текущего счетчика медитаций.
    """
    # Получаем текущие данные пользователя
    user_data = await state.get_data()
    
    # Получаем текущий счетчик медитаций или устанавливаем 0, если счетчика нет
    meditation_count = user_data.get("user_meditation_count", 0)
    
    # Формируем сообщение с информацией о счетчике
    message_text = f"📊 <b>Информация о медитациях</b>\n\n"
    message_text += f"Использовано медитаций: <b>{meditation_count}</b> из <b>{MAX_MEDITATION_COUNT}</b>\n"
    
    if meditation_count >= MAX_MEDITATION_COUNT:
        message_text += "\n⚠️ Вы достигли максимального количества медитаций. "
        message_text += "Если вы чувствуете, что готовы к новой — напишите нам отдельно, и мы обсудим."
    else:
        remaining = MAX_MEDITATION_COUNT - meditation_count
        message_text += f"\nОсталось доступных медитаций: <b>{remaining}</b>"
    
    # Отправляем сообщение с информацией
    await message.answer(message_text, parse_mode="HTML")
    logger.info(f"Пользователь {message.from_user.id} запросил информацию о счетчике медитаций: {meditation_count}")

# Добавляем обработчик для сброса счетчика медитаций (только для администраторов)
@meditation_router.message(Command("reset_meditation_count"))
async def cmd_reset_meditation_count(message: Message, state: FSMContext):
    """
    Обработчик команды /reset_meditation_count для сброса счетчика медитаций.
    Доступно только администраторам.
    """
    # Проверяем, является ли пользователь администратором
    # В реальном приложении здесь будет проверка ID пользователя или другой механизм
    admin_ids = [
        123456789,  # Заменить на реальный ID администратора
    ]
    
    # Если пользователь не администратор, отправляем сообщение об ошибке
    if message.from_user.id not in admin_ids:
        await message.answer(
            "⛔ У вас нет прав для выполнения этой команды."
        )
        logger.warning(f"Пользователь {message.from_user.id} попытался сбросить счетчик медитаций без прав")
        return
    
    # Получаем текущие данные пользователя
    user_data = await state.get_data()
    
    # Получаем текущий счетчик медитаций
    old_count = user_data.get("user_meditation_count", 0)
    
    # Сбрасываем счетчик медитаций
    await state.update_data(user_meditation_count=0)
    
    # Отправляем сообщение об успешном сбросе
    await message.answer(
        f"✅ Счетчик медитаций сброшен с {old_count} на 0."
    )
    logger.info(f"Администратор {message.from_user.id} сбросил счетчик медитаций с {old_count} на 0")

# Добавляем обработчик для сброса счетчика медитаций для конкретного пользователя (только для администраторов)
@meditation_router.message(Command("reset_user_meditation"))
async def cmd_reset_user_meditation(message: Message):
    """
    Обработчик команды /reset_user_meditation для сброса счетчика медитаций конкретного пользователя.
    Формат: /reset_user_meditation USER_ID
    Доступно только администраторам.
    """
    # Проверяем, является ли пользователь администратором
    admin_ids = [
        123456789,  # Заменить на реальный ID администратора
    ]
    
    # Если пользователь не администратор, отправляем сообщение об ошибке
    if message.from_user.id not in admin_ids:
        await message.answer(
            "⛔ У вас нет прав для выполнения этой команды."
        )
        logger.warning(f"Пользователь {message.from_user.id} попытался сбросить счетчик медитаций другого пользователя без прав")
        return
    
    # Разбираем команду для получения ID пользователя
    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.answer(
            "❌ Неверный формат команды. Используйте: /reset_user_meditation USER_ID"
        )
        return
    
    try:
        target_user_id = int(command_parts[1])
    except ValueError:
        await message.answer(
            "❌ Неверный ID пользователя. ID должен быть числом."
        )
        return
    
    try:
        # Получаем диспетчер для доступа к хранилищу состояний
        from aiogram import Bot
        bot = Bot.get_current()
        dp = bot.dispatcher
        
        # Создаем ключ для хранилища состояний
        from aiogram.fsm.storage.base import StorageKey
        key = StorageKey(bot_id=bot.id, user_id=target_user_id, chat_id=target_user_id)
        
        # Получаем данные пользователя из хранилища
        data = await dp.storage.get_data(key)
        
        # Получаем текущий счетчик медитаций
        old_count = data.get("user_meditation_count", 0)
        
        # Обновляем счетчик медитаций
        data["user_meditation_count"] = 0
        await dp.storage.set_data(key, data)
        
        # Отправляем сообщение об успешном сбросе
        await message.answer(
            f"✅ Счетчик медитаций для пользователя {target_user_id} сброшен с {old_count} на 0."
        )
        logger.info(f"Администратор {message.from_user.id} сбросил счетчик медитаций пользователя {target_user_id} с {old_count} на 0")
        
    except Exception as e:
        logger.error(f"Ошибка при сбросе счетчика медитаций пользователя {target_user_id}: {e}")
        await message.answer(
            f"❌ Произошла ошибка при сбросе счетчика медитаций: {str(e)}"
        ) 