from datetime import date, datetime
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.params import Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.sql_database import get_db
from app.utils.security import get_current_user
from app.utils.image_upload import save_file
from app.model.users_model import User, Student, LogEntry, SupervisorReviews, UserRole, ApprovalStatus
from app.schema.users_schema import LogEntryResponse, ReviewCreate


log_router = APIRouter()


class SupervisorLogResponse(BaseModel):
    id: int
    student_id: int
    student_name: str
    matric_number: str
    title: str
    activity_description: str
    hours_worked: float
    log_date: date
    status: str

    class Config:
        from_attributes = True



@log_router.post("/create", response_model=LogEntryResponse, status_code=status.HTTP_201_CREATED)
def create_daily_log(
    log_date: str = Form(...),
    title: str = Form(...),
    hours_worked: int = Form(...),
    activity_description: str = Form(...),
    skills_acquired: Optional[str] = Form(None),
    challenges_faced: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Students can create a daily logbook entry."""
    if current_user.role != UserRole.student:
        raise HTTPException(status_code=403, detail="Only students can create log entries.")
    
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found.")

    # 1. Convert the incoming string date into a Python date object
    try:
        parsed_date = datetime.strptime(log_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
        
    # Check for duplicate log dates using the parsed date object
    existing_log = db.query(LogEntry).filter(
        LogEntry.student_id == student.id, 
        LogEntry.log_date == parsed_date
    ).first()
    if existing_log:
        raise HTTPException(status_code=400, detail="A log entry for this date already exists.")

    # 2. Save file and get path string
    file_path_url = save_file(file, subfolder="logs")

    # 3. Create log record
    db_log = LogEntry(
        student_id=student.id,
        log_date=parsed_date,  # <--- Pass the python date object here
        title=title,
        hours_worked=hours_worked,
        activity_description=activity_description,
        skills_acquired=skills_acquired,
        challenges_faced=challenges_faced,
        evidence_file_url=file_path_url, 
        status=ApprovalStatus.pending
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


@log_router.get("/all/{student_id}", response_model=List[LogEntryResponse])
def get_logs(
    student_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch logs based on user roles (Student views own logs; Supervisors view assigned students)."""
    
    if current_user.role == UserRole.student:
        return db.query(LogEntry).filter(LogEntry.student_id == student_id).all()
    
    elif current_user.role in [UserRole.industry_supervisor, UserRole.institution_supervisor]:
        if not student_id:
            raise HTTPException(status_code=400, detail="student_id parameter is required for supervisors.")
        return db.query(LogEntry).filter(LogEntry.student_id == student_id).all()
    
    elif current_user.role == UserRole.admin:
        query = db.query(LogEntry)
        if student_id:
            query = query.filter(LogEntry.student_id == student_id)
        return query.all()
        
    raise HTTPException(status_code=403, detail="Unauthorized access.")


@log_router.put("/update/{log_id}", response_model=LogEntryResponse)
def update_daily_log(
    log_id: int,
    log_date: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    hours_worked: Optional[int] = Form(None),
    activity_description: Optional[str] = Form(None),
    skills_acquired: Optional[str] = Form(None),
    challenges_faced: Optional[str] = Form(None),
    status: Optional[str] = Form(None), # Supervisors can update approval status
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Students and supervisors can update daily logbook entries."""
    allowed_roles = [UserRole.student, UserRole.industry_supervisor, UserRole.institution_supervisor, UserRole.admin]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Unauthorized to update log entries.")

    # Fetch the target log entry
    db_log = db.query(LogEntry).filter(LogEntry.id == log_id).first()
    if not db_log:
        raise HTTPException(status_code=404, detail="Log entry not found.")

    # Role-specific restrictions for students
    if current_user.role == UserRole.student:
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if not student or db_log.student_id != student.id:
            raise HTTPException(status_code=403, detail="You can only update your own log entries.")
        
        # Prevent students from editing already approved logs
        if db_log.status == ApprovalStatus.approved:
            raise HTTPException(status_code=400, detail="Cannot edit an approved log entry.")

    # 1. Update and validate date if provided
    if log_date:
        try:
            parsed_date = datetime.strptime(log_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
        
        # Check for duplicate log dates excluding the current log itself
        existing_log = db.query(LogEntry).filter(
            LogEntry.student_id == db_log.student_id, 
            LogEntry.log_date == parsed_date,
            LogEntry.id != log_id
        ).first()
        if existing_log:
            raise HTTPException(status_code=400, detail="A log entry for this date already exists.")
        db_log.log_date = parsed_date

    # 2. Update optional fields if provided
    if title is not None:
        db_log.title = title
    if hours_worked is not None:
        db_log.hours_worked = hours_worked
    if activity_description is not None:
        db_log.activity_description = activity_description
    if skills_acquired is not None:
        db_log.skills_acquired = skills_acquired
    if challenges_faced is not None:
        db_log.challenges_faced = challenges_faced
        
    # Allow supervisors/admins to update the status directly if supplied
    if status is not None and current_user.role != UserRole.student:
        try:
            db_log.status = ApprovalStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status value.")

    # 3. Handle optional new file upload
    if file:
        file_path_url = save_file(file, subfolder="logs")
        db_log.evidence_file_url = file_path_url

    db.commit()
    db.refresh(db_log)
    return db_log


@log_router.delete("/delete/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_daily_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Students and supervisors can delete daily logbook entries."""
    allowed_roles = [UserRole.student, UserRole.industry_supervisor, UserRole.institution_supervisor, UserRole.admin]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Unauthorized to delete log entries.")

    # Fetch the target log entry
    db_log = db.query(LogEntry).filter(LogEntry.id == log_id).first()
    if not db_log:
        raise HTTPException(status_code=404, detail="Log entry not found.")

    # Role-specific restrictions for students
    if current_user.role == UserRole.student:
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if not student or db_log.student_id != student.id:
            raise HTTPException(status_code=403, detail="You can only delete your own log entries.")
        
        # Prevent students from deleting already approved logs
        if db_log.status == ApprovalStatus.approved:
            raise HTTPException(status_code=400, detail="Cannot delete an approved log entry.")

    db.delete(db_log)
    db.commit()
    return None



@log_router.get("/supervisor/pending-logs", response_model=List[LogEntryResponse])
def get_supervisor_pending_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch pending logs for students assigned to the current supervisor or all pending if admin."""
    if current_user.role not in [UserRole.industry_supervisor, UserRole.institution_supervisor, UserRole.admin]:
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    # If admin, return all pending logs. If supervisor, filter by assigned students.
    query = db.query(LogEntry).filter(LogEntry.status == ApprovalStatus.pending)
    
    if current_user.role == UserRole.industry_supervisor:
        query = query.filter(
            LogEntry.student_id.in_(
                db.query(Student.id).filter(Student.industry_supervisor_id == current_user.id)
            )
        )

    if current_user.role == UserRole.institution_supervisor:
        query = query.filter(
            LogEntry.student_id.in_(
                db.query(Student.id).filter(Student.institution_supervisor_id == current_user.id)
            )
        )

    return query.all()


@log_router.get("/supervisor/students")
def get_supervisor_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch list of assigned trainees with compliance and pending counts."""
    if current_user.role not in [UserRole.industry_supervisor, UserRole.institution_supervisor, UserRole.admin]:
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    query = db.query(Student)
    
    # ✅ Filter Student model directly, not via LogEntry
    if current_user.role == UserRole.industry_supervisor:
        query = query.filter(Student.industry_supervisor_id == current_user.id)

    if current_user.role == UserRole.institution_supervisor:
        query = query.filter(Student.institution_supervisor_id == current_user.id)
        
    students = query.all()
    
    # Format response to match frontend expectations (compliance, week, pending count)
    result = []
    for student in students:
        pending_count = db.query(LogEntry).filter(
            LogEntry.student_id == student.id, 
            LogEntry.status == ApprovalStatus.pending
        ).count()
        
        result.append({
            "id": student.id,
            "name": f"{student.user.full_name}" if hasattr(student, "user") else "Student",
            "matric": student.matric_number,
            "dept": getattr(student, "department", "Engineering"),
            "week": getattr(student, "current_week", 1),
            "compliance": getattr(student, "compliance_rate", 85),
            "pending": pending_count
        })
        
    return result


@log_router.get("/supervisor/all-logs", response_model=List[SupervisorLogResponse])
def get_all_supervisor_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch all log entries submitted by all students assigned to the currently authenticated industry supervisor.
    """
    # 1. Verify the user is an industry supervisor
    if current_user.role != UserRole.industry_supervisor and current_user.role != UserRole.institution_supervisor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only industry supervisors can view supervisor logs."
        )

    # 2. Query students assigned to this supervisor using industry_supervisor_id
    # We join with the User table to get the student's full name
    assigned_students_query = (
        db.query(Student, User)
        .join(User, Student.user_id == User.id)
        .filter(Student.industry_supervisor_id == current_user.id)
        .all()
    )

    if not assigned_students_query:
        return []

    # Map student.id to their info for fast lookup
    student_map = {}
    student_ids = []
    for student, user_profile in assigned_students_query:
        student_ids.append(student.id)
        student_map[student.id] = {
            "full_name": user_profile.full_name,
            "matric_number": student.matric_number
        }

    # 3. Query all log entries belonging to these student IDs
    logs = db.query(LogEntry).filter(LogEntry.student_id.in_(student_ids)).all()

    # 4. Format and return response
    results = []
    for log in logs:
        student_info = student_map.get(log.student_id, {"full_name": "Unknown Trainee", "matric_number": "N/A"})
        results.append(
            SupervisorLogResponse(
                id=log.id,
                student_id=log.student_id,
                student_name=student_info["full_name"],
                matric_number=student_info["matric_number"],
                title=log.title,
                activity_description=log.activity_description,
                hours_worked=log.hours_worked,
                log_date=log.log_date,
                status=log.status.value if hasattr(log.status, "value") else log.status
            )
        )

    return results

