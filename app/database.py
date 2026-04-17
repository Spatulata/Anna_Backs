from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongo:3zzc8t1bephxkkvn@192.168.1.182:27019/")
DATABASE_NAME = os.getenv("DATABASE_NAME", "diary_db")

client: AsyncIOMotorClient = None
database = None


async def connect_to_mongo():
    """Подключение к MongoDB"""
    global client, database
    try:
        client = AsyncIOMotorClient(MONGODB_URL)
        database = client[DATABASE_NAME]
        # Проверка подключения
        await client.admin.command('ping')
        print(f"✅ Подключено к MongoDB: {DATABASE_NAME}")
    except ConnectionFailure as e:
        print(f"❌ Ошибка подключения к MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Закрытие подключения к MongoDB"""
    global client
    if client:
        client.close()
        print("🔌 Подключение к MongoDB закрыто")


async def init_db():
    """Инициализация базы данных"""
    await connect_to_mongo()
    
    # Создание индексов
    await database.users.create_index("email", unique=True)
    await database.users.create_index("username", unique=True)
    await database.grades.create_index([("student_id", 1), ("date", -1)])
    await database.homework.create_index([("class_id", 1), ("date", -1)])
    await database.schedule.create_index([("class_id", 1), ("day_of_week", 1)])


def get_database():
    """Получение объекта базы данных"""
    return database
