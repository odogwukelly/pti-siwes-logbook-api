from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime
from typing import Optional
from app.model.users_model import UserRole, ApprovalStatus

# Token Schemas
class userData(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

class Token(BaseModel):
    user_data: Optional[userData] = None
    access_token: str


class TokenPayload(BaseModel):
    sub: Optional[int] = None
    role: Optional[str] = None

# Log Entry Creation & Response
class LogEntryCreate(BaseModel):
    log_date: date
    title: str 
    activity_description: str = Field(..., min_length=10)
    skills_acquired: Optional[str] = None
    challenges_faced: Optional[str] = None
    evidence_file_url: Optional[str] = None

class LogEntryResponse(BaseModel):
    id: int
    student_id: int
    hours_worked: int
    log_date: date
    title: str
    activity_description: str
    skills_acquired: Optional[str]
    challenges_faced: Optional[str]
    evidence_file_url: Optional[str]
    status: ApprovalStatus
    created_at: datetime

    class Config:
        from_attributes = True

# Supervisor Review Schema
class ReviewCreate(BaseModel):
    status_action: ApprovalStatus  # approved or rejected
    feedback_comments: Optional[str] = None