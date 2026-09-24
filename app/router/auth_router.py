from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import timedelta
from app.db.sql_database import get_db
from app.model.users_model import User, Student, UserRole
from app.schema.users_schema import Token
from app.config import settings
from app.utils.security import create_access_token, generate_otp, hash_password, verify_password, verify_otp
from app.utils.emailService import send_otp_email


auth_router = APIRouter()
time = settings.OTP_DURATION

class EmailRequest(BaseModel):
    email: EmailStr
    fullName: str
    matric_number: str
    role: str

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: UserRole
    matric_number: Optional[str] = None
    department: Optional[str] = None
    industrial_organization: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    role: str


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(
    register_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new user (Student, Industry Supervisor, or Institution Supervisor)."""
    existing_user = db.query(User).filter(User.email == register_data.email , User.role == register_data.role).first()
    existing_student = db.query(Student).filter(Student.matric_number == register_data.matric_number).first()
    if existing_user:
        raise HTTPException(status_code=400, detail=f"Email is already registered.")
    if existing_student:
        raise HTTPException(status_code=400, detail=f"Student with this matric number is already registered.")

    if register_data.role == UserRole.student:
        if not register_data.matric_number or not register_data.department or not register_data.industrial_organization:
            raise HTTPException(
                status_code=400, 
                detail="Students must provide matric_number, department, and industrial_organization."
            )

    hashed_password = hash_password(register_data.password)
    user = User(
        email=register_data.email,
        password_hash=hashed_password,
        full_name=register_data.full_name,
        role=register_data.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # If the registered user is a student, create their student profile record
    if register_data.role == UserRole.student:
        student_profile = Student(
            user_id=user.id,
            matric_number=register_data.matric_number,
            department=register_data.department,
            industrial_organization=register_data.industrial_organization
        )
        db.add(student_profile)
        db.commit()

    return {"message": "User registered successfully", "user_id": user.id}

@auth_router.post("/send-otp")
def send_otp_route(data: EmailRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == data.email , User.role == data.role).first()
    existing_student = db.query(Student).filter(Student.matric_number == data.matric_number).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    if existing_student:
        raise HTTPException(
            status_code=400, 
            detail="Student with this matric number is already registered."
        )

    
    otp = generate_otp(db, data.email)
    sent = send_otp_email(data.email, otp, time, data.fullName )
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send OTP")
    return {"msg": "OTP sent successfully"}

@auth_router.post("/verify-otp")
def verify_otp_route(data: VerifyOtpRequest, db: Session = Depends(get_db)):
    is_valid, message = verify_otp(data.email, data.otp, db)
    
    if not is_valid:
        # ❌ Wrong OTP or expired or not found
        raise HTTPException(status_code=400, detail=message)

    # ✅ OTP verified successfully
    return {"success": True, "message": message}

@auth_router.post("/login", response_model=Token)
def login_for_access_token(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Authenticate user credentials and return a JWT access token."""
    user = db.query(User).filter(User.email == login_data.email, User.role == login_data.role).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token({"sub": login_data.email, "role": login_data.role})

    return {"user_data": user, "access_token": access_token}