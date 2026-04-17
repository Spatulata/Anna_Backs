from fastapi import APIRouter, Depends, HTTPException
from app.models import ScheduleCreate, ScheduleResponse
from app.auth import get_current_active_user, require_role, UserRole
from app.database import get_database
from typing import List, Optional
from datetime import datetime, timezone
from bson import ObjectId

router = APIRouter()


@router.post("/", response_model=ScheduleResponse)
async def create_schedule_item(
    schedule_data: ScheduleCreate,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.TEACHER]))
):
    """Создание элемента расписания (только для админов и учителей)"""
    db = get_database()
    
    # Проверка существования класса, предмета и учителя
    try:
        class_obj = await db.classes.find_one({"_id": ObjectId(schedule_data.class_id)})
        if not class_obj:
            raise HTTPException(status_code=404, detail="Класс не найден")
        
        subject = await db.subjects.find_one({"_id": ObjectId(schedule_data.subject_id)})
        if not subject:
            raise HTTPException(status_code=404, detail="Предмет не найден")
        
        teacher = await db.users.find_one({"_id": ObjectId(schedule_data.teacher_id)})
        if not teacher or teacher.get("role") != "teacher":
            raise HTTPException(status_code=404, detail="Учитель не найден")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Неверный формат ID")
    
    schedule_dict = {
        **schedule_data.dict(),
        "created_at": datetime.now(timezone.utc)
    }
    
    result = await db.schedule.insert_one(schedule_dict)
    schedule_dict["id"] = str(result.inserted_id)
    schedule_dict.pop("_id", None)
    
    return ScheduleResponse(**schedule_dict)


@router.get("/class/{class_id}", response_model=List[ScheduleResponse])
async def get_class_schedule(
    class_id: str,
    day_of_week: Optional[int] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Получение расписания для класса"""
    db = get_database()
    
    query = {"class_id": class_id}
    
    if day_of_week is not None:
        query["day_of_week"] = day_of_week
    
    schedule_list = await db.schedule.find(query).sort("day_of_week", 1).sort("lesson_number", 1).to_list(length=1000)
    
    for schedule in schedule_list:
        schedule["id"] = str(schedule["_id"])
        schedule.pop("_id", None)
    
    return [ScheduleResponse(**schedule) for schedule in schedule_list]


@router.get("/student/{student_id}", response_model=List[ScheduleResponse])
async def get_student_schedule(
    student_id: str,
    day_of_week: Optional[int] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Получение расписания для ученика"""
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

    query = {"class_id": class_id}

    if day_of_week is not None:
        query["day_of_week"] = day_of_week

    schedule_list = await db.schedule.find(query).sort("day_of_week", 1).sort("lesson_number", 1).to_list(length=1000)

    for schedule in schedule_list:
        schedule["id"] = str(schedule["_id"])
        schedule.pop("_id", None)

    return [ScheduleResponse(**schedule) for schedule in schedule_list]


@router.get("/teacher/{teacher_id}", response_model=List[ScheduleResponse])
async def get_teacher_schedule(
    teacher_id: str,
    day_of_week: Optional[int] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Получение расписания учителя"""
    db = get_database()

    # Учитель видит только своё расписание
    if current_user["role"] == "teacher" and teacher_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Нет доступа")

    query = {"teacher_id": teacher_id}

    if day_of_week is not None:
        query["day_of_week"] = day_of_week

    schedule_list = await db.schedule.find(query).sort("day_of_week", 1).sort("lesson_number", 1).to_list(length=1000)

    for schedule in schedule_list:
        schedule["id"] = str(schedule["_id"])
        schedule.pop("_id", None)

    return [ScheduleResponse(**schedule) for schedule in schedule_list]
