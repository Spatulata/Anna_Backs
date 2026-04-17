from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    PARENT = "parent"
    ADMIN = "admin"


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    role: UserRole


class UserCreate(UserBase):
    password: str
    class_id: Optional[str] = None  # Для учеников и родителей
    child_ids: Optional[List[str]] = None  # Для родителей


class UserResponse(UserBase):
    id: str
    class_id: Optional[str] = None
    child_ids: Optional[List[str]] = None
    created_at: datetime
    is_banned: bool = False

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    class_id: Optional[str] = None
    child_ids: Optional[List[str]] = None
    is_banned: Optional[bool] = None


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class ClassBase(BaseModel):
    name: str
    grade: int  # Номер класса (1-11)
    letter: str  # Буква класса (А, Б, В...)


class ClassCreate(ClassBase):
    pass


class ClassResponse(ClassBase):
    id: str
    students: List[str] = []  # IDs учеников
    teachers: List[str] = []  # IDs учителей

    class Config:
        from_attributes = True


class SubjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class SubjectCreate(SubjectBase):
    pass


class SubjectResponse(SubjectBase):
    id: str

    class Config:
        from_attributes = True


class GradeBase(BaseModel):
    student_id: str
    subject_id: str
    value: int = Field(..., ge=1, le=5)  # Оценка от 1 до 5
    date: date
    comment: Optional[str] = None


class GradeCreate(GradeBase):
    teacher_id: str


class GradeResponse(GradeBase):
    id: str
    teacher_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class HomeworkBase(BaseModel):
    class_id: str
    subject_id: str
    title: str
    description: str
    due_date: date


class HomeworkCreate(HomeworkBase):
    teacher_id: str


class HomeworkResponse(HomeworkBase):
    id: str
    teacher_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class ScheduleBase(BaseModel):
    class_id: str
    subject_id: str
    teacher_id: str
    day_of_week: int = Field(..., ge=0, le=6)  # 0 - понедельник, 6 - воскресенье
    lesson_number: int = Field(..., ge=1, le=8)  # Номер урока
    room: Optional[str] = None


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleResponse(ScheduleBase):
    id: str

    class Config:
        from_attributes = True
