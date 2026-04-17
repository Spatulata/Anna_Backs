from fastapi import APIRouter, Depends, HTTPException
from app.models import UserResponse, UserUpdate, UserCreate
from app.auth import get_current_active_user, require_role, UserRole, get_password_hash
from app.database import get_database
from typing import List
from bson import ObjectId
from datetime import datetime, timezone

router = APIRouter()


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Создание нового пользователя (только для админов)"""
    db = get_database()

    existing = await db.users.find_one({
        "$or": [
            {"username": user_data.username},
            {"email": user_data.email}
        ]
    })
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь с таким именем или email уже существует")

    user_dict = {
        "username": user_data.username,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "role": user_data.role.value,
        "hashed_password": get_password_hash(user_data.password),
        "class_id": user_data.class_id,
        "child_ids": user_data.child_ids or [],
        "is_banned": False,
        "created_at": datetime.now(timezone.utc)
    }

    result = await db.users.insert_one(user_dict)
    user_dict["id"] = str(result.inserted_id)

    if user_data.role == UserRole.STUDENT and user_data.class_id:
        try:
            await db.classes.update_one(
                {"_id": ObjectId(user_data.class_id)},
                {"$push": {"students": str(result.inserted_id)}}
            )
        except:
            pass

    user_dict.pop("hashed_password", None)
    user_dict.pop("_id", None)
    return UserResponse(**user_dict)


@router.get("/", response_model=List[UserResponse])
async def get_users(current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.TEACHER]))):
    """Получение списка всех пользователей"""
    db = get_database()
    users = await db.users.find({}).to_list(length=200)
    for user in users:
        user["id"] = str(user["_id"])
        user.pop("hashed_password", None)
        user.pop("_id", None)
        if "is_banned" not in user:
            user["is_banned"] = False
    return [UserResponse(**user) for user in users]


# === СПЕЦИФИЧНЫЕ РОУТЫ (должны идти ДО общих /{user_id}) ===

@router.get("/admin/stats")
async def get_admin_stats(current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    """Статистика системы"""
    db = get_database()
    return {
        "total_users": await db.users.count_documents({}),
        "admins": await db.users.count_documents({"role": "admin"}),
        "teachers": await db.users.count_documents({"role": "teacher"}),
        "students": await db.users.count_documents({"role": "student"}),
        "parents": await db.users.count_documents({"role": "parent"}),

        "classes": await db.classes.count_documents({}),
        "subjects": await db.subjects.count_documents({}),
        "grades": await db.grades.count_documents({}),
        "homework": await db.homework.count_documents({}),
    }





# === ОБЩИЕ РОУТЫ (после специфичных) ===

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, current_user: dict = Depends(get_current_active_user)):
    """Получение информации о пользователе"""
    db = get_database()
    if current_user["role"] == "parent" and user_id not in current_user.get("child_ids", []):
        raise HTTPException(status_code=403, detail="Нет доступа")
    if current_user["role"] == "student" and user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Нет доступа")

    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user["id"] = str(user["_id"])
    user.pop("hashed_password", None)
    user.pop("_id", None)
    if "is_banned" not in user:
        user["is_banned"] = False
    return UserResponse(**user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Обновление данных пользователя"""
    db = get_database()
    try:
        obj_id = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="Некорректный ID")

    existing = await db.users.find_one({"_id": obj_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    update_fields = {}
    if user_data.full_name is not None: update_fields["full_name"] = user_data.full_name
    if user_data.email is not None: update_fields["email"] = user_data.email
    if user_data.role is not None: update_fields["role"] = user_data.role.value
    if user_data.class_id is not None: update_fields["class_id"] = user_data.class_id
    if user_data.child_ids is not None: update_fields["child_ids"] = user_data.child_ids


    if update_fields:
        await db.users.update_one({"_id": obj_id}, {"$set": update_fields})

    updated = await db.users.find_one({"_id": obj_id})
    updated["id"] = str(updated["_id"])
    updated.pop("hashed_password", None)
    updated.pop("_id", None)
    if "is_banned" not in updated:
        updated["is_banned"] = False
    return UserResponse(**updated)


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Удаление пользователя"""
    db = get_database()
    try:
        obj_id = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="Некорректный ID")

    existing = await db.users.find_one({"_id": obj_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if str(obj_id) == current_user["id"]:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")

    await db.users.delete_one({"_id": obj_id})
    return {"message": f"Пользователь {existing['username']} удалён"}
