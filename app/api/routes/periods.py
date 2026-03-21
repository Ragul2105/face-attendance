"""
API routes for period management and period-based attendance.
"""

from fastapi import APIRouter, HTTPException, Depends, Form
from typing import List, Optional
from datetime import datetime

from app.api.routes.auth import get_current_user, UserInfo, require_staff_user
from app.models.period import Period, PeriodCreate, PeriodAttendance, PeriodAttendanceCreate
from app.services.period_service import PeriodService
from app.services.email_service import EmailService
from app.utils.timezone_utils import now_ist
from app.db.firebase_client import get_firestore

router = APIRouter()


# ==================== PERIOD MANAGEMENT ====================

@router.post("/periods", response_model=Period)
async def create_period(
    periodNumber: int = Form(...),
    name: str = Form(...),
    startTime: str = Form(...),  # "HH:MM"
    endTime: str = Form(...),  # "HH:MM"
    dayOfWeek: int = Form(...),  # 0-6
    classId: str = Form(...),
    campusLatitude: Optional[float] = Form(None),
    campusLongitude: Optional[float] = Form(None),
    locationRadiusMeters: Optional[float] = Form(200.0),
    current_user: UserInfo = Depends(require_staff_user),
):
    """Create a new period (teachers only)."""
    period_create = PeriodCreate(
        periodNumber=periodNumber,
        name=name,
        startTime=startTime,
        endTime=endTime,
        dayOfWeek=dayOfWeek,
        classId=classId,
        campusLatitude=campusLatitude,
        campusLongitude=campusLongitude,
        locationRadiusMeters=locationRadiusMeters,
    )
    
    period_service = PeriodService()
    return period_service.create_period(period_create, current_user.userId)


@router.get("/periods/class/{class_id}", response_model=List[Period])
async def get_class_periods(
    class_id: str,
    day_of_week: Optional[int] = None,
    current_user: UserInfo = Depends(get_current_user),
):
    """Get all periods for a class (optionally filtered by day)."""
    period_service = PeriodService()
    return period_service.get_periods_for_class(class_id, day_of_week)


@router.get("/periods/{period_id}", response_model=Period)
async def get_period(
    period_id: str,
    current_user: UserInfo = Depends(get_current_user),
):
    """Get a specific period."""
    period_service = PeriodService()
    period = period_service.get_period(period_id)
    
    if not period:
        raise HTTPException(status_code=404, detail="Period not found")
    
    return period


@router.put("/periods/{period_id}", response_model=Period)
async def update_period(
    period_id: str,
    name: Optional[str] = Form(None),
    startTime: Optional[str] = Form(None),
    endTime: Optional[str] = Form(None),
    dayOfWeek: Optional[int] = Form(None),
    campusLatitude: Optional[float] = Form(None),
    campusLongitude: Optional[float] = Form(None),
    locationRadiusMeters: Optional[float] = Form(None),
    isActive: Optional[bool] = Form(None),
    current_user: UserInfo = Depends(require_staff_user),
):
    """Update a period (teachers only)."""
    period_service = PeriodService()
    
    updates = {}
    if name is not None:
        updates["name"] = name
    if startTime is not None:
        updates["startTime"] = startTime
    if endTime is not None:
        updates["endTime"] = endTime
    if dayOfWeek is not None:
        updates["dayOfWeek"] = dayOfWeek
    if campusLatitude is not None:
        updates["campusLatitude"] = campusLatitude
    if campusLongitude is not None:
        updates["campusLongitude"] = campusLongitude
    if locationRadiusMeters is not None:
        updates["locationRadiusMeters"] = locationRadiusMeters
    if isActive is not None:
        updates["isActive"] = isActive
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    period = period_service.update_period(period_id, updates)
    
    if not period:
        raise HTTPException(status_code=404, detail="Period not found")
    
    return period


@router.delete("/periods/{period_id}")
async def deactivate_period(
    period_id: str,
    current_user: UserInfo = Depends(require_staff_user),
):
    """Deactivate a period."""
    period_service = PeriodService()
    period_service.deactivate_period(period_id)
    
    return {"message": "Period deactivated successfully"}


# ==================== PERIOD ATTENDANCE ====================

@router.post("/attendance/period", response_model=PeriodAttendance)
async def mark_period_attendance(
    periodId: str = Form(...),
    classId: str = Form(...),
    attendanceDate: str = Form(...),  # "YYYY-MM-DD"
    status: str = Form("present"),
    studentLatitude: Optional[float] = Form(None),
    studentLongitude: Optional[float] = Form(None),
    current_user: UserInfo = Depends(get_current_user),
):
    """Mark attendance for a period (students mark their own attendance)."""
    period_service = PeriodService()

    if current_user.role == "student" and status != "present":
        raise HTTPException(status_code=403, detail="Students can only mark present status")
    
    attendance_create = PeriodAttendanceCreate(
        userId=current_user.userId,
        periodId=periodId,
        classId=classId,
        attendanceDate=attendanceDate,
        status=status,
        studentLatitude=studentLatitude,
        studentLongitude=studentLongitude,
    )
    
    try:
        return period_service.mark_period_attendance(
            attendance_create, 
            enforce_period_window=False
        )
    except ValueError as e:
        message = str(e)
        if "already marked" in message.lower():
            raise HTTPException(status_code=409, detail=message)
        raise HTTPException(status_code=400, detail=message)


@router.get("/attendance/student/{student_id}")
async def get_student_period_attendance(
    student_id: str,
    current_user: UserInfo = Depends(get_current_user),
):
    """Get period attendance records for a student."""
    # Verify user is viewing their own attendance or is staff
    if current_user.userId != student_id and current_user.role == "student":
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    period_service = PeriodService()
    return period_service.get_attendance_for_student(student_id)


@router.get("/attendance/period/{period_id}/{attendance_date}")
async def get_period_attendance(
    period_id: str,
    attendance_date: str,  # "YYYY-MM-DD"
    current_user: UserInfo = Depends(require_staff_user),
):
    """Get all attendance records for a period on a date (teachers only)."""
    period_service = PeriodService()
    return period_service.get_attendance_for_period(period_id, attendance_date)


@router.get("/attendance/absent/{period_id}/{class_id}/{attendance_date}")
async def get_absent_students(
    period_id: str,
    class_id: str,
    attendance_date: str,  # "YYYY-MM-DD"
    current_user: UserInfo = Depends(require_staff_user),
):
    """Get list of absent students for a period (teachers only)."""
    period_service = PeriodService()
    return period_service.get_absent_students_for_period(period_id, class_id, attendance_date)


@router.post("/attendance/mark-absent/{period_id}/{class_id}/{attendance_date}")
async def mark_absent_for_period(
    period_id: str,
    class_id: str,
    attendance_date: str,
    current_user: UserInfo = Depends(require_staff_user),
):
    """Mark all absent students for a period and send emails (teachers only)."""
    period_service = PeriodService()
    email_service = EmailService()
    
    # Get period info
    period = period_service.get_period(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Period not found")
    
    # Mark absent
    result = period_service.mark_bulk_absent(period_id, class_id, attendance_date)
    
    # Send absence emails
    absent_students = period_service.get_absent_students_for_period(period_id, class_id, attendance_date)
    
    email_recipients = [
        {
            "email": student["email"],
            "name": student["name"],
            "teacher_name": current_user.name,
        }
        for student in absent_students
        if student.get("email")
    ]
    
    if email_recipients:
        email_result = email_service.send_bulk_absence_notifications(
            email_recipients, period.name, class_id, attendance_date
        )
        result["emails_sent"] = email_result["sent"]
        result["emails_failed"] = email_result["failed"]
    
    return result


@router.get("/attendance/summary/{student_id}/{class_id}")
async def get_attendance_summary(
    student_id: str,
    class_id: str,
    current_user: UserInfo = Depends(get_current_user),
):
    """Get attendance summary for a student in a class."""
    # Verify permission
    if current_user.userId != student_id and current_user.role == "student":
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    period_service = PeriodService()
    return period_service.get_attendance_summary(class_id, student_id)
