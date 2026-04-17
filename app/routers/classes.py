from fastapi import APIRouter, Depends, HTTPException
from app.models import ClassCreate, ClassResponse, UserResponse
from app.auth import get_current_active_user, require_role, UserRole
from app.database import get_database
from typing import List
from datetime import datetime, timezone
from bson import ObjectId

router = APIRouter()


@router.post("/", response_model=ClassResponse)
async def create_class(
    class_data: ClassCreate,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Создание нового класса (только для админов)"""
    db = get_database()
    
    # Проверка существования класса
    existing = await db.classes.find_one({
        "grade": class_data.grade,
        "letter": class_data.letter.upper()
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Класс уже существует")
    
    class_dict = {
        **class_data.dict(),
        "letter": class_data.letter.upper(),
        "students": [],
        "teachers": [],
        "created_at": datetime.now(timezone.utc)
    }
    
    result = await db.classes.insert_one(class_dict)
    class_dict["id"] = str(result.inserted_id)
    class_dict.pop("_id", None)
    
    return ClassResponse(**class_dict)


@router.get("/", response_model=List[ClassResponse])
async def get_classes(current_user: dict = Depends(get_current_active_user)):
    """Получение списка классов"""
    db = get_database()
    classes = await db.classes.find({}).sort("grade", 1).to_list(length=100)
    
    for cls in classes:
        cls["id"] = str(cls["_id"])
        cls.pop("_id", None)
    
    return [ClassResponse(**cls) for cls in classes]


@router.get("/{class_id}", response_model=ClassResponse)
async def get_class(class_id: str, current_user: dict = Depends(get_current_active_user)):
    """Получение информации о классе"""
    db = get_database()
    
    cls = await db.classes.find_one({"_id": ObjectId(class_id)})
    if not cls:
        raise HTTPException(status_code=404, detail="Класс не найден")
    
    cls["id"] = str(cls["_id"])
    cls.pop("_id", None)

    return ClassResponse(**cls)


@router.get("/{class_id}/students", response_model=List[UserResponse])
async def get_class_students(
    class_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Получение списка учеников класса"""
    db = get_database()

    cls = await db.classes.find_one({"_id": ObjectId(class_id)})
    if not cls:
        raise HTTPException(status_code=404, detail="Класс не найден")

    student_ids = cls.get("students", [])
    if not student_ids:
        return []

    students = await db.users.find({"_id": {"$in": [ObjectId(sid) for sid in student_ids]}}).to_list(length=100)

    for s in students:
        s["id"] = str(s["_id"])
        s.pop("hashed_password", None)
        s.pop("_id", None)
        if "is_banned" not in s:
            s["is_banned"] = False

    return [UserResponse(**s) for s in students]
