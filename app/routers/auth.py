from fastapi import APIRouter, Depends, HTTPException, status
from datetime import timedelta, datetime, timezone
from app.models import UserCreate, UserLogin, Token, UserResponse
from app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_active_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.database import get_database
from bson import ObjectId

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """Регистрация нового пользователя"""
    db = get_database()
    
    # Проверка существования пользователя
    existing_user = await db.users.find_one({
        "$or": [
            {"username": user_data.username},
            {"email": user_data.email}
        ]
    })
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем или email уже существует"
        )
    
    # Создание пользователя
    user_dict = {
        "username": user_data.username,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "role": user_data.role.value,
        "hashed_password": get_password_hash(user_data.password),
        "class_id": user_data.class_id,
        "child_ids": user_data.child_ids or [],
        "created_at": datetime.now(timezone.utc)
    }
    
    result = await db.users.insert_one(user_dict)
    user_dict["id"] = str(result.inserted_id)
    user_dict["_id"] = result.inserted_id
    
    # Удаляем пароль из ответа
    user_dict.pop("hashed_password", None)
    user_dict.pop("_id", None)
    
    return UserResponse(**user_dict)


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Авторизация пользователя"""
    db = get_database()
    
    user = await db.users.find_one({"username": credentials.username})
    
    if not user or not verify_password(credentials.password, user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Создание токена
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["_id"])},
        expires_delta=access_token_expires
    )
    
    user["id"] = str(user["_id"])
    user.pop("hashed_password", None)
    user.pop("_id", None)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(**user)
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_active_user)):
    """Получение информации о текущем пользователе"""
    return UserResponse(**current_user)
