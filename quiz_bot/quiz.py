from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types
import json

# Структура квиза из JSON
with open('quiz.json') as file:
    quiz_data = json.load(file)
    print(quiz_data)

# Создаем кнопки для выбора ответов квиза
def generate_options_keyboard(answer_options, correct_option):
    builder = InlineKeyboardBuilder()

    for idx, option in enumerate(answer_options):
        # В callback_data передаем индекс выбранного варианта
        builder.add(types.InlineKeyboardButton(
            text=option,
            callback_data=f"answer_{idx}"  # Пример: "answer_0", "answer_1" и т.д.
        ))

    builder.adjust(1)
    return builder.as_markup()