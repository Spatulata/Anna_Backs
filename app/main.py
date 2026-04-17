import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, users, classes, subjects, grades, homework, schedule
from app.database import init_db

app = FastAPI(title="Электронный дневник школьника", version="1.0.0")

# CORS: разрешаем origins из переменной CORS_ORIGINS (через запятую) или "*" для всех
_cors_env = os.getenv("CORS_ORIGINS", "*").strip()
_cors_origins = ["*"] if _cors_env == "*" else [o.strip() for o in _cors_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True if _cors_env != "*" else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth.router, prefix="/api/auth", tags=["Авторизация"])
app.include_router(users.router, prefix="/api/users", tags=["Пользователи"])
app.include_router(classes.router, prefix="/api/classes", tags=["Классы"])
app.include_router(subjects.router, prefix="/api/subjects", tags=["Предметы"])
app.include_router(grades.router, prefix="/api/grades", tags=["Оценки"])
app.include_router(homework.router, prefix="/api/homework", tags=["Домашние задания"])
app.include_router(schedule.router, prefix="/api/schedule", tags=["Расписание"])


@app.on_event("startup")
async def startup_event():
    """Инициализация базы данных при запуске"""
    await init_db()


@app.get("/")
async def root():
    return {"message": "API электронного дневника школьника"}


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

