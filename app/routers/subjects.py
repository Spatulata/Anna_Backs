from fastapi import APIRouter, Depends, HTTPException
from app.models import SubjectCreate, SubjectResponse
from app.auth import get_current_active_user, require_role, UserRole
from app.database import get_database
from typing import List
from datetime import datetime, timezone
from bson import ObjectId

router = APIRouter()


@router.post("/", response_model=SubjectResponse)
async def create_subject(
    subject_data: SubjectCreate,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Создание нового предмета (только для админов)"""
    db = get_database()
    
    existing = await db.subjects.find_one({"name": subject_data.name})
    if existing:
        raise HTTPException(status_code=400, detail="Предмет уже существует")
    
    subject_dict = {
        **subject_data.dict(),
        "created_at": datetime.now(timezone.utc)
    }
    
    result = await db.subjects.insert_one(subject_dict)
    subject_dict["id"] = str(result.inserted_id)
    subject_dict.pop("_id", None)
    
    return SubjectResponse(**subject_dict)


@router.get("/", response_model=List[SubjectResponse])
async def get_subjects(current_user: dict = Depends(get_current_active_user)):
    """Получение списка предметов"""
    db = get_database()
    subjects = await db.subjects.find({}).sort("name", 1).to_list(length=100)
    
    for subject in subjects:
        subject["id"] = str(subject["_id"])
        subject.pop("_id", None)
    
    return [SubjectResponse(**subject) for subject in subjects]


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(subject_id: str, current_user: dict = Depends(get_current_active_user)):
    """Получение информации о предмете"""
    db = get_database()
    
    subject = await db.subjects.find_one({"_id": ObjectId(subject_id)})
    if not subject:
        raise HTTPException(status_code=404, detail="Предмет не найден")
    
    subject["id"] = str(subject["_id"])
    subject.pop("_id", None)
    
    return SubjectResponse(**subject)
