from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types

# Структура квиза в JSON


# quiz_data = [
#     {
#         "question": "Что такое Python?",
#         "options": ["Язык программирования", "Тип данных", "Музыкальный инструмент", "Змея на английском"],
#         "correct_option": 0
#     },
#     {
#         "question": "Какой тип данных используется для хранения целых чисел в Python?",
#         "options": ["int", "float", "str", "list"],
#         "correct_option": 0
#     },
#     {
#         "question": "Какой метод списка в Python используется для добавления элемента в конец списка?",
#         "options": ["add()", "insert()", "append()", "extend()"],
#         "correct_option": 2
#     }
# ]


quiz_data = [
    {
        "question": "Что такое Python?",
        "options": ["Язык программирования", "Тип данных", "Музыкальный инструмент", "Змея на английском"],
        "correct_option": 0
    },
    {
        "question": "Какой тип данных используется для хранения целых чисел в Python?",
        "options": ["int", "float", "str", "list"],
        "correct_option": 0
    },
    {
        "question": "Какой метод списка в Python используется для добавления элемента в конец списка?",
        "options": ["add()", "insert()", "append()", "extend()"],
        "correct_option": 2
    },
    {
        "question": "Какая команда используется для вывода текста в консоль в Python?",
        "options": ["output()", "print()", "console.log()", "echo()"],
        "correct_option": 1
    },
    {
        "question": "Что вернет выражение len('Hello, World!') в Python?",
        "options": ["10", "12", "13", "11"],
        "correct_option": 2
    },
    {
        "question": "Что делает нейронная сеть при обучении?",
        "options": ["Создает новые данные", "Находит закономерности в них", "Отправляет данные в интернет", "Хранит данные без изменений"],
        "correct_option": 0
    },
    {
        "question": "Какой алгоритм часто используется для оптимизации нейронных сетей?",
        "options": ["Бинарный поиск", "Градиентный спуск", "Сортировка пузырьком", "Рекурсия"],
        "correct_option": 1
    },
    {
        "question": "Что такое веса (weights) в нейронной сети?",
        "options": ["Данные входного слоя", "Функции активации", "Выходные значения", "Параметры модели"],
        "correct_option": 3
    },
    {
        "question": "Какой метод используется в TensorFlow для запуска обучения нейронной сети?",
        "options": ["train()", "fit()", "learn()", "execute()"],
        "correct_option": 1
    },
    {
        "question": "Что такое функция потерь (loss function) в нейронных сетях?",
        "options": ["Мера ошибки модели", "Скорость обучения", "Количество слоев", "Точность предсказания"],
        "correct_option": 0
    }
]


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