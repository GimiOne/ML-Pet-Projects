import asyncio
from aiogram import Bot, Dispatcher
# Импортируем API токен из конфиг-файла
from config import API_TOKEN
# Импортируем хендлеры
from handlers import setup_handlers
# Импортируем метод для создания таблиц
from database import create_table

# Объект бота
bot = Bot(token=API_TOKEN)
# Диспетчер
dp = Dispatcher()


async def main():
    # Создаем таблицу базы данных
    await create_table()
    # Регистрируем хэндлеры
    setup_handlers(dp)
    # Запускаем процесс поллинга новых апдейтов
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())