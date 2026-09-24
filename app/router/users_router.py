from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.sql_database import get_db
from app.utils.security import get_current_user
from app.model.users_model import User, Student, UserRole
from pydantic import BaseModel

users_router = APIRouter()

class StudentProfileResponse(BaseModel):
    id: Optional[int] = None  # Matches database Integer type
    user_id: Optional[int] = None
    matric_number: Optional[str] = None
    department: Optional[str] = None
    industrial_organization: Optional[str] = None
    industry_supervisor_id: Optional[int] = None
    institution_supervisor_id: Optional[int] = None

    class Config:
        from_attributes = True

class UserProfileResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool

    class Config:
        from_attributes = True

class ProfileResponse(BaseModel):
    user_data: UserProfileResponse
    profile_data: Optional[StudentProfileResponse] = None

    class Config:
        from_attributes = True

@users_router.get("/me", response_model=ProfileResponse)
def read_users_me(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Fetch the currently authenticated user's profile details."""
    
    student_profile = None
    if current_user.role == UserRole.student:
        student_profile = db.query(Student).filter(Student.user_id == current_user.id).first()
        
    return {
        "user_data": current_user,
        "profile_data": student_profile or None
    }


@users_router.get("/{user_id}")
def read_users_me(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Fetch the currently authenticated user's profile details."""
    
    user = db.query(User).filter(User.id == user_id).first()
        
    return user


@users_router.get("/all-user/{role}")
def read_users(
    role: str, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Fetch all user profile details by role with proper validation."""

    # 1. Validate role string against UserRole enum values
    valid_roles = [r.value for r in UserRole]
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role specified.")

    # 2. Optional: Restrict access (e.g., only Admin or Supervisors can view lists)
    # if current_user.role not in [UserRole.admin, UserRole.institution_supervisor]:
    #     raise HTTPException(status_code=403, detail="Not authorized to access this resource.")

    profile_data = []

    # 3. Query appropriately based on role schema structure
    if role == UserRole.student:
        # Join Student with User using student.user_id to fetch common attributes together
        # This returns tuples or you can structure them into a combined dictionary response
        results = (
            db.query(Student, User)
            .join(User, Student.user_id == User.id)
            .all()
        )
        
        # Format the response cleanly so the frontend gets a flat/rich structure
        formatted_students = []
        for student, user in results:
            formatted_students.append({
                "id": student.id,
                "user_id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role,
                "matric_number": student.matric_number,
                "department": student.department,
                "industry_supervisor_id": student.industry_supervisor_id,
                "institution_supervisor_id": student.institution_supervisor_id,
                "industrial_organization": getattr(student, "industrial_organization", None),
            })
        return formatted_students
    else:
        profile_data = db.query(User).filter(User.role == role).all()

    return profile_data

@users_router.patch("/assign-student/{student_id}")
def assign_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Allows industry or institution supervisors to assign students"""
    if current_user.role == UserRole.student:
        raise HTTPException(status_code=403, detail="Unauthorized role access.")

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student record not found.")

    # Dynamically assign based on the supervisor's specific role type
    if current_user.role == UserRole.industry_supervisor: # or your specific industry role enum value
        student.industry_supervisor_id = current_user.id
    elif current_user.role == UserRole.institution_supervisor: # or your specific institution role enum value
        student.institution_supervisor_id = current_user.id
    else:
        # Fallback or generic assignment if applicable
        student.institution_supervisor_id = current_user.id

    db.commit()
    db.refresh(student)

    return {"msg": "Student assigned successfully!"}


@users_router.patch("/unassign-student/{student_id}")
def unassign_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Allows industry or institution supervisors to unassign students"""
    if current_user.role == UserRole.student:
        raise HTTPException(status_code=403, detail="Unauthorized role access.")

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student record not found.")

    # Dynamically clear based on the supervisor's specific role type
    if current_user.role == UserRole.industry_supervisor:
        if student.industry_supervisor_id != current_user.id:
            raise HTTPException(status_code=403, detail="This student is not assigned to you.")
        student.industry_supervisor_id = None
        
    elif current_user.role == UserRole.institution_supervisor:
        if student.institution_supervisor_id != current_user.id:
            raise HTTPException(status_code=403, detail="This student is not assigned to you.")
        student.institution_supervisor_id = None
        
    else:
        # Admin or fallback role can clear fields as needed
        student.industry_supervisor_id = None
        student.institution_supervisor_id = None

    db.commit()
    db.refresh(student)

    return {"msg": "Student unassigned successfully!"}
