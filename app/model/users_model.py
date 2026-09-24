import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, Date, ForeignKey, Enum, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.sql_database import Base

class UserRole(str, enum.Enum):
    student = "student"
    industry_supervisor = "industry_supervisor"
    institution_supervisor = "institution_supervisor"
    admin = "admin"

class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=False, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ADD foreign_keys HERE:
    student_profile = relationship(
        "Student", 
        back_populates="user", 
        foreign_keys="[Student.user_id]", 
        uselist=False, 
        cascade="all, delete-orphan"
    )

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    matric_number = Column(String(100), unique=True, index=True, nullable=False)
    department = Column(String(150), nullable=False)
    industrial_organization = Column(String(255), nullable=False)
    industry_supervisor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    institution_supervisor_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    user = relationship("User", back_populates="student_profile", foreign_keys=[user_id])
    log_entries = relationship("LogEntry", back_populates="student", cascade="all, delete-orphan")


class LogEntry(Base):
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    hours_worked = Column(Integer, nullable=False)
    log_date = Column(Date, nullable=False)
    title = Column(String(255), nullable=False)
    activity_description = Column(Text, nullable=False)
    skills_acquired = Column(String(255), nullable=True)
    challenges_faced = Column(Text, nullable=True)
    evidence_file_url = Column(String(500), nullable=True)
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.pending)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="log_entries")
    reviews = relationship("SupervisorReviews", back_populates="log_entry", cascade="all, delete-orphan")

class SupervisorReviews(Base):
    __tablename__ = "supervisor_reviews"

    id = Column(Integer, primary_key=True, index=True)
    log_entry_id = Column(Integer, ForeignKey("log_entries.id", ondelete="CASCADE"), nullable=False)
    supervisor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status_action = Column(Enum(ApprovalStatus), nullable=False)
    feedback_comments = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), server_default=func.now())

    log_entry = relationship("LogEntry", back_populates="reviews")