from fastapi import APIRouter, Depends, HTTPException
from app.models import GradeCreate, GradeResponse
from app.auth import get_current_active_user, require_role, UserRole
from app.database import get_database
from typing import List, Optional
from datetime import datetime, date, timezone
from bson import ObjectId
from pydantic import BaseModel

router = APIRouter()


class GradeUpdate(BaseModel):
    value: Optional[int] = None
    date: Optional[date] = None
    comment: Optional[str] = None


@router.post("/", response_model=GradeResponse)
async def create_grade(
    grade_data: GradeCreate,
    current_user: dict = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN]))
):
    """Создание оценки (только для учителей и админов)"""
    db = get_database()

    # Проверка существования ученика и предмета
    try:
        student = await db.users.find_one({"_id": ObjectId(grade_data.student_id)})
        if not student or student.get("role") != "student":
            raise HTTPException(status_code=404, detail="Ученик не найден")

        subject = await db.subjects.find_one({"_id": ObjectId(grade_data.subject_id)})
        if not subject:
            raise HTTPException(status_code=404, detail="Предмет не найден")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Неверный формат ID")

    grade_dict = {
        **grade_data.dict(),
        "teacher_id": current_user["id"],
        "date": grade_data.date.isoformat(),  # Конвертируем date в строку ISO
        "created_at": datetime.now(timezone.utc)
    }

    result = await db.grades.insert_one(grade_dict)
    grade_dict["id"] = str(result.inserted_id)
    grade_dict.pop("_id", None)

    return GradeResponse(**grade_dict)


@router.get("/student/{student_id}", response_model=List[GradeResponse])
async def get_student_grades(
    student_id: str,
    subject_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Получение оценок ученика"""
    db = get_database()

    # Проверка доступа
    if current_user["role"] == "student" and student_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Нет доступа")

    if current_user["role"] == "parent" and student_id not in current_user.get("child_ids", []):
        raise HTTPException(status_code=403, detail="Нет доступа")

    query = {"student_id": student_id}

    if subject_id:
        query["subject_id"] = subject_id

    if start_date:
        query["date"] = {"$gte": start_date.isoformat()}

    if end_date:
        if "date" in query and isinstance(query["date"], dict):
            query["date"]["$lte"] = end_date.isoformat()
        elif "date" not in query:
            query["date"] = {"$lte": end_date.isoformat()}
        else:
            # Если date уже строка, заменяем на диапазон
            old_date = query["date"]
            query["date"] = {"$gte": old_date, "$lte": end_date.isoformat()}

    grades = await db.grades.find(query).sort("date", -1).to_list(length=1000)

    for grade in grades:
        grade["id"] = str(grade["_id"])
        grade.pop("_id", None)

    return [GradeResponse(**grade) for grade in grades]


@router.get("/class/{class_id}/subject/{subject_id}", response_model=List[GradeResponse])
async def get_class_grades_by_subject(
    class_id: str,
    subject_id: str,
    current_user: dict = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN]))
):
    """Получение оценок всех учеников класса по предмету (для учителя)"""
    db = get_database()

    # Получаем учеников класса
    try:
        class_obj = await db.classes.find_one({"_id": ObjectId(class_id)})
    except:
        raise HTTPException(status_code=400, detail="Неверный формат ID класса")

    if not class_obj:
        raise HTTPException(status_code=404, detail="Класс не найден")

    student_ids = class_obj.get("students", [])
    if not student_ids:
        return []

    grades = await db.grades.find({
        "student_id": {"$in": student_ids},
        "subject_id": subject_id
    }).sort("date", -1).to_list(length=5000)

    for grade in grades:
        grade["id"] = str(grade["_id"])
        grade.pop("_id", None)

    return [GradeResponse(**grade) for grade in grades]


@router.get("/{grade_id}", response_model=GradeResponse)
async def get_grade(grade_id: str, current_user: dict = Depends(get_current_active_user)):
    """Получение информации об оценке"""
    db = get_database()

    try:
        grade = await db.grades.find_one({"_id": ObjectId(grade_id)})
    except:
        raise HTTPException(status_code=404, detail="Оценка не найдена")

    if not grade:
        raise HTTPException(status_code=404, detail="Оценка не найдена")

    # Проверка доступа
    if current_user["role"] == "student" and grade["student_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Нет доступа")

    if current_user["role"] == "parent" and grade["student_id"] not in current_user.get("child_ids", []):
        raise HTTPException(status_code=403, detail="Нет доступа")

    grade["id"] = str(grade["_id"])
    grade.pop("_id", None)

    return GradeResponse(**grade)


@router.put("/{grade_id}", response_model=GradeResponse)
async def update_grade(
    grade_id: str,
    grade_data: GradeUpdate,
    current_user: dict = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN]))
):
    """Обновление оценки (только для учителей и админов)"""
    db = get_database()

    try:
        obj_id = ObjectId(grade_id)
    except:
        raise HTTPException(status_code=400, detail="Некорректный ID оценки")

    existing = await db.grades.find_one({"_id": obj_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Оценка не найдена")

    update_fields = {}
    if grade_data.value is not None:
        if grade_data.value < 1 or grade_data.value > 5:
            raise HTTPException(status_code=400, detail="Оценка должна быть от 1 до 5")
        update_fields["value"] = grade_data.value
    if grade_data.date is not None:
        update_fields["date"] = grade_data.date.isoformat()
    if grade_data.comment is not None:
        update_fields["comment"] = grade_data.comment

    if update_fields:
        await db.grades.update_one({"_id": obj_id}, {"$set": update_fields})

    updated = await db.grades.find_one({"_id": obj_id})
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)

    return GradeResponse(**updated)


@router.delete("/{grade_id}")
async def delete_grade(
    grade_id: str,
    current_user: dict = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN]))
):
    """Удаление оценки (только для учителей и админов)"""
    db = get_database()

    try:
        obj_id = ObjectId(grade_id)
    except:
        raise HTTPException(status_code=400, detail="Некорректный ID оценки")

    existing = await db.grades.find_one({"_id": obj_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Оценка не найдена")

    await db.grades.delete_one({"_id": obj_id})

    return {"message": "Оценка удалена"}
