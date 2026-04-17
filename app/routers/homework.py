from fastapi import APIRouter, Depends, HTTPException
from app.models import HomeworkCreate, HomeworkResponse
from app.auth import get_current_active_user, require_role, UserRole
from app.database import get_database
from typing import List, Optional
from datetime import datetime, date, timezone
from bson import ObjectId

router = APIRouter()


@router.post("/", response_model=HomeworkResponse)
async def create_homework(
    homework_data: HomeworkCreate,
    current_user: dict = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN]))
):
    """Создание домашнего задания (только для учителей и админов)"""
    db = get_database()
    
    # Проверка существования класса и предмета
    try:
        class_obj = await db.classes.find_one({"_id": ObjectId(homework_data.class_id)})
        if not class_obj:
            raise HTTPException(status_code=404, detail="Класс не найден")
        
        subject = await db.subjects.find_one({"_id": ObjectId(homework_data.subject_id)})
        if not subject:
            raise HTTPException(status_code=404, detail="Предмет не найден")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Неверный формат ID")
    
    homework_dict = {
        **homework_data.dict(),
        "teacher_id": current_user["id"],
        "due_date": homework_data.due_date.isoformat(),  # Конвертируем date в строку ISO
        "created_at": datetime.now(timezone.utc)
    }
    
    result = await db.homework.insert_one(homework_dict)
    homework_dict["id"] = str(result.inserted_id)
    homework_dict.pop("_id", None)
    
    return HomeworkResponse(**homework_dict)


@router.get("/class/{class_id}", response_model=List[HomeworkResponse])
async def get_class_homework(
    class_id: str,
    subject_id: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Получение домашних заданий для класса"""
    db = get_database()
    
    # Проверка доступа
    if current_user["role"] == "student":
        if current_user.get("class_id") != class_id:
            raise HTTPException(status_code=403, detail="Нет доступа")
    
    query = {"class_id": class_id}
    
    if subject_id:
        query["subject_id"] = subject_id
    
    homework_list = await db.homework.find(query).sort("due_date", 1).to_list(length=1000)
    
    for homework in homework_list:
        homework["id"] = str(homework["_id"])
        homework.pop("_id", None)
    
    return [HomeworkResponse(**homework) for homework in homework_list]


@router.get("/student/{student_id}", response_model=List[HomeworkResponse])
async def get_student_homework(
    student_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Получение домашних заданий для ученика"""
    db = get_database()
    
    # Проверка доступа
    if current_user["role"] == "student" and student_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Нет доступа")
    
    if current_user["role"] == "parent" and student_id not in current_user.get("child_ids", []):
        raise HTTPException(status_code=403, detail="Нет доступа")
    
    # Получаем класс ученика
    try:
        student = await db.users.find_one({"_id": ObjectId(student_id)})
    except:
        raise HTTPException(status_code=404, detail="Ученик не найден")
    
    if not student:
        raise HTTPException(status_code=404, detail="Ученик не найден")
    
    class_id = student.get("class_id")
    if not class_id:
        return []
    
    homework_list = await db.homework.find({"class_id": class_id}).sort("due_date", 1).to_list(length=1000)
    
    for homework in homework_list:
        homework["id"] = str(homework["_id"])
        homework.pop("_id", None)
    
    return [HomeworkResponse(**homework) for homework in homework_list]


@router.get("/{homework_id}", response_model=HomeworkResponse)
async def get_homework(homework_id: str, current_user: dict = Depends(get_current_active_user)):
    """Получение информации о домашнем задании"""
    db = get_database()
    
    try:
        homework = await db.homework.find_one({"_id": ObjectId(homework_id)})
    except:
        raise HTTPException(status_code=404, detail="Домашнее задание не найдено")
    
    if not homework:
        raise HTTPException(status_code=404, detail="Домашнее задание не найдено")
    
    homework["id"] = str(homework["_id"])
    homework.pop("_id", None)
    
    return HomeworkResponse(**homework)
