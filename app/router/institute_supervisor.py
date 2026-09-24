from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.sql_database import get_db
from app.model.users_model import SupervisorReviews, User, Student, LogEntry, UserRole, ApprovalStatus
# Import your authentication dependency (e.g., get_current_active_user)
from app.utils.security import get_current_user

institute_supervisor_router = APIRouter()

@institute_supervisor_router.get("/dashboard")
def get_institution_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Ensure the user is an institution supervisor
    if current_user.role != UserRole.institution_supervisor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Institution supervisor role required."
        )

    # 1. Fetch students assigned to this institution supervisor
    students = db.query(Student).filter(Student.institution_supervisor_id == current_user.id).all()
    student_ids = [s.id for s in students]
    total_students = len(students)

    # 2. Fetch log entries for these students
    logs = db.query(LogEntry).filter(LogEntry.student_id.in_(student_ids)).all() if student_ids else []
    
    total_logs = len(logs)
    approved_logs = sum(1 for l in logs if l.status == ApprovalStatus.approved)
    compliance_rate = round((approved_logs / total_logs * 100) if total_logs > 0 else 0)

    # 3. Aggregate Department Compliance Stats
    dept_data = {}
    for s in students:
        if s.department not in dept_data:
            dept_data[s.department] = {"total": 0, "approved": 0}
        s_logs = [l for l in logs if l.student_id == s.id]
        dept_data[s.department]["total"] += len(s_logs)
        dept_data[s.department]["approved"] += sum(1 for l in s_logs if l.status == ApprovalStatus.approved)

    department_stats_list = []
    for dept, counts in dept_data.items():
        rate = round((counts["approved"] / counts["total"] * 100) if counts["total"] > 0 else 0)
        department_stats_list.append({"dept": dept, "compliance": rate})

    # If no department data exists yet, provide fallback sample formatting for the chart
    if not department_stats_list:
        department_stats_list = [{"dept": "General Eng.", "compliance": compliance_rate}]

    # 4. Build Student Compliance Table Rows
    student_rows = []
    for s in students:
        s_logs = [l for l in logs if l.student_id == s.id]
        s_total = len(s_logs)
        s_approved = sum(1 for l in s_logs if l.status == ApprovalStatus.approved)
        s_pending = sum(1 for l in s_logs if l.status == ApprovalStatus.pending)
        s_compliance = round((s_approved / s_total * 100) if s_total > 0 else 0)
        
        # Estimate week index based on log volume or fallback to 1
        week_count = min(s_total, 24)
        status = "active" if s_compliance >= 40 or s_total == 0 else "flagged"

        student_rows.append({
            "id": s.id,
            "name": s.user.full_name if s.user else "Student",
            "matric": s.matric_number,
            "dept": s.department,
            "week": week_count,
            "compliance": s_compliance,
            "pending": s_pending,
            "status": status
        })

    return {
        "total_students": total_students,
        "active_placements": total_students, # Can be filtered by active status if applicable
        "approvals_issued": approved_logs,
        "compliance_rate": f"{compliance_rate}%",
        "department_stats": department_stats_list,
        "student_compliance": student_rows,
        "monthly_approvals": [
            {"month": "May", "submitted": int(total_logs * 0.15), "approved": int(approved_logs * 0.15)},
            {"month": "Jun", "submitted": int(total_logs * 0.2), "approved": int(approved_logs * 0.2)},
            {"month": "Jul", "submitted": int(total_logs * 0.25), "approved": int(approved_logs * 0.25)},
            {"month": "Aug", "submitted": int(total_logs * 0.2), "approved": int(approved_logs * 0.2)},
            {"month": "Sep", "submitted": int(total_logs * 0.1), "approved": int(approved_logs * 0.1)},
            {"month": "Oct", "submitted": int(total_logs * 0.1), "approved": int(approved_logs * 0.1)},
        ]
    }





class ApprovalActionRequest(BaseModel):
    status_action: ApprovalStatus  # approved or rejected
    feedback_comments: Optional[str] = None

@institute_supervisor_router.get("/approvals")
def get_institution_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.institution_supervisor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Institution supervisor role required."
        )

    # 1. Fetch students assigned to this institution supervisor
    students = db.query(Student).filter(Student.institution_supervisor_id == current_user.id).all()
    student_ids = [s.id for s in students]

    if not student_ids:
        return []

    # 2. Fetch log entries for these students (e.g., pending or all recent logs)
    logs = db.query(LogEntry).filter(LogEntry.student_id.in_(student_ids)).order_by(LogEntry.created_at.desc()).all()

    response_items = []
    for log in logs:
        student = db.query(Student).filter(Student.id == log.student_id).first()
        student_user = db.query(User).filter(User.id == student.user_id).first() if student else None
        
        # Get latest review or fallback info
        latest_review = db.query(SupervisorReviews).filter(SupervisorReviews.log_entry_id == log.id).order_by(SupervisorReviews.reviewed_at.desc()).first()
        
        industry_sign_name = "Industry Supervisor"
        if student and student.industry_supervisor_id:
            ind_user = db.query(User).filter(User.id == student.industry_supervisor_id).first()
            if ind_user:
                industry_sign_name = ind_user.full_name

        response_items.append({
            "id": log.id,
            "student": {
                "id": student.id if student else 0,
                "name": student_user.full_name if student_user else "Unknown Student",
                "matric": student.matric_number if student else "N/A",
                "week": min(log.id, 24) # Estimated or derived week index
            },
            "date": log.log_date.strftime("%b %d, %Y") if log.log_date else "Recent",
            "industry_sign_off_text": f"{industry_sign_name} · {log.log_date.strftime('%b %d') if log.log_date else ''}",
            "hours": log.hours_worked,
            "status": log.status.value,
            "title": log.title,
            "activity_description": log.activity_description,
            "skills_acquired": log.skills_acquired,
            "challenges_faced": log.challenges_faced,
            "evidence_file_url": log.evidence_file_url
        })

    return response_items


@institute_supervisor_router.post("/approvals/{log_id}")
def review_institution_log(
    log_id: int,
    payload: ApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.institution_supervisor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Institution supervisor role required."
        )

    log_entry = db.query(LogEntry).filter(LogEntry.id == log_id).first()
    if not log_entry:
        raise HTTPException(status_code=404, detail="Log entry not found")

    # Verify student belongs to this supervisor's oversight
    student = db.query(Student).filter(Student.id == log_entry.student_id).first()
    if not student or student.institution_supervisor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to review this student's log")

    # Update log status
    log_entry.status = payload.status_action
    
    # Record supervisor review audit log
    review = SupervisorReviews(
        log_entry_id=log_entry.id,
        supervisor_id=current_user.id,
        status_action=payload.status_action,
        feedback_comments=payload.feedback_comments
    )
    db.add(review)
    db.commit()
    db.refresh(log_entry)

    return {"message": f"Log entry successfully {payload.status_action.value}", "status": log_entry.status}






