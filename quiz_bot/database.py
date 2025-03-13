import aiosqlite

# Импортируем название БД из конфиг-файла
from config import DB_NAME
from quiz import quiz_data

async def create_table():
    # Создаем соединение с базой данных
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица состояния квиза
        await db.execute('''
            CREATE TABLE IF NOT EXISTS quiz_state (
                user_id INTEGER PRIMARY KEY,
                question_index INTEGER
            )
        ''')
        # Таблица результатов пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_results (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                last_result_correct INTEGER,
                last_result_total INTEGER
            )
        ''')
        await db.commit()

async def save_quiz_result(user_id, username, correct_count, total_count):
    """
    Сохраняет результат прохождения квиза.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT OR REPLACE INTO user_results (user_id, username, last_result_correct, last_result_total)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, correct_count, total_count))
        await db.commit()

async def get_all_results():
    """
    Возвращает все результаты пользователей.
    """
    results = []
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT user_id, username, last_result_correct, last_result_total FROM user_results') as cursor:
            async for row in cursor:
                user_id, username, correct_count, total_count = row
                results.append({
                    "user_id": user_id,
                    "username": username or f"User_{user_id}",
                    "result": f"{correct_count}/{total_count}"
                })
    return results


async def get_quiz_index(user_id):
     # Подключаемся к базе данных
     async with aiosqlite.connect(DB_NAME) as db:
        # Получаем запись для заданного пользователя
        async with db.execute('SELECT question_index FROM quiz_state WHERE user_id = (?)', (user_id, )) as cursor:
            # Возвращаем результат
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0


async def get_quiz_answers(user_id):
     # Подключаемся к базе данных
     async with aiosqlite.connect(DB_NAME) as db:
        # Получаем запись для заданного пользователя
        async with db.execute('SELECT question_index FROM quiz_state WHERE user_id = (?)', (user_id, )) as cursor:
            # Возвращаем результат
            results = await cursor.fetchone()
            if results is not None:
                print(results)
                return results[0]
            else:
                return 0


async def update_quiz_index(user_id, index):
    # Создаем соединение с базой данных (если она не существует, она будет создана)
    async with aiosqlite.connect(DB_NAME) as db:
        # Вставляем новую запись или заменяем ее, если с данным user_id уже существует
        await db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index) VALUES (?, ?)', (user_id, index))
        # Сохраняем изменения
        await db.commit()


user_answers = {}
async def save_answer(user_id, question_index, answer):
    """
    Сохраняет ответ пользователя.
    """
    if user_id not in user_answers:
        user_answers[user_id] = []
    user_answers[user_id].append({
        "answer": answer,
        "is_correct": answer == quiz_data[question_index]['options'][quiz_data[question_index]['correct_option']]
    })


async def show_user_answers(user_id):
    """
    Показывает все сохраненные ответы пользователя.
    """
    if user_id not in user_answers or not user_answers[user_id]:
        return "Вы еще не ответили ни на один вопрос."

    response = "Ваши ответы:\n"
    for idx, answer_data in enumerate(user_answers[user_id], start=1):
        is_correct = "✅" if answer_data["is_correct"] else "❌"
        response += f"{idx}. {answer_data['answer']} {is_correct}\n"

    return response