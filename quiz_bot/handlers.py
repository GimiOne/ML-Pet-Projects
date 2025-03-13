import logging
from aiogram.filters.command import Command
from aiogram import F, types, Bot, Dispatcher, types
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from database import get_quiz_index, update_quiz_index, save_answer, show_user_answers, user_answers, save_quiz_result, get_all_results
from quiz import quiz_data, generate_options_keyboard
from aiogram import F
from config import DB_NAME

# Настройка логирования
logging.basicConfig(level=logging.INFO)


def setup_handlers(dp):
    """
    Регистрация всех обработчиков команд и коллбэков.
    """
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_quiz, Command("quiz"))
    dp.message.register(cmd_stats, Command("stats"))
    dp.message.register(cmd_quiz, F.text == "Начать игру")
    dp.message.register(cmd_stats, F.text == "Статистика")  # Новая команда
    dp.callback_query.register(process_answer, F.data.startswith("answer_"))  # Обработчик ответов


async def cmd_start(message: types.Message):
    """
    Обработчик команды /start.
    """
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Начать игру"))

    # Добавляем кнопку "Статистика" (можно поместить на новую строку)
    builder.row(types.KeyboardButton(text="Статистика"))

    await message.answer(
        "Добро пожаловать в квиз! Нажмите кнопку 'Начать игру', чтобы начать.",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )


async def cmd_quiz(message: types.Message):
    """
    Обработчик команды /quiz или кнопки 'Начать игру'.
    """
    await message.answer("Давайте начнем квиз!")
    await new_quiz(message)


async def process_answer(callback: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку с ответом.
    """
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )

    # Получаем текущий вопрос
    current_question_index = await get_quiz_index(callback.from_user.id)

    # Извлекаем индекс выбранного варианта из callback_data
    selected_option_index = int(callback.data.split("_")[1])  # Пример: "answer_0" -> 0
    selected_answer = quiz_data[current_question_index]['options'][selected_option_index]

    # Сохраняем выбранный ответ
    await save_answer(
        callback.from_user.id,
        current_question_index,
        selected_answer
    )

    # Проверяем правильность ответа
    correct_option_index = quiz_data[current_question_index]['correct_option']
    if selected_option_index == correct_option_index:
        await callback.message.answer("Верно!")
    else:
        correct_answer = quiz_data[current_question_index]['options'][correct_option_index]
        await callback.message.answer(f"Неправильно. Правильный ответ: {correct_answer}")

    # Переходим к следующему вопросу
    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index)

    if current_question_index < len(quiz_data):
        await get_question(callback.message, callback.from_user.id)
    else:
        # Подсчитываем результаты
        correct_count = sum(1 for answer in user_answers[callback.from_user.id] if answer["is_correct"])
        total_count = len(quiz_data)

        # Сохраняем результат
        await save_quiz_result(
            callback.from_user.id,
            callback.from_user.username,
            correct_count,
            total_count
        )

        # Выводим ответы пользователя
        answers_summary = await show_user_answers(callback.from_user.id)
        await callback.message.answer("Это был последний вопрос. Квиз завершен!")
        await callback.message.answer(answers_summary)

        # Выводим результат
        result_message = f"Вы ответили правильно на {correct_count} из {total_count} вопросов."
        await callback.message.answer(result_message)


dp = Dispatcher()
@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """
    Команда /stats для просмотра статистики всех игроков.
    """
    results = await get_all_results()
    if not results:
        await message.answer("Пока что никто не прошел квиз.")
        return

    response = "Статистика игроков:\n"
    for idx, result in enumerate(results, start=1):
        response += f"{idx}. {result['username']}: {result['result']} ✅\n"

    await message.answer(response)


async def get_question(message, user_id):
    """
    Отправляет следующий вопрос пользователю.
    """
    current_question_index = await get_quiz_index(user_id)
    correct_index = quiz_data[current_question_index]['correct_option']
    opts = quiz_data[current_question_index]['options']
    kb = generate_options_keyboard(opts, correct_index)
    await message.answer(f"{quiz_data[current_question_index]['question']}", reply_markup=kb)


async def new_quiz(message):
    """
    Начинает новый квиз для пользователя.
    """
    user_id = message.from_user.id

    # Очищаем предыдущие ответы пользователя
    if user_id in user_answers:
        user_answers[user_id] = []  # Очистка списка ответов

    current_question_index = 0
    await update_quiz_index(user_id, current_question_index)
    await get_question(message, user_id)