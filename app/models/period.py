"""
Period management models for class schedules and attendance tracking per period.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class Period(BaseModel):
    """Period schema for request/response."""
    periodId: str
    classId: str
    periodNumber: int  # 1, 2, 3, etc.
    name: str  # "Period 1", "Math", etc.
    startTime: str  # "HH:MM" format (IST)
    endTime: str  # "HH:MM" format (IST)
    dayOfWeek: int  # 0=Monday, 6=Sunday
    campusLatitude: Optional[float] = None
    campusLongitude: Optional[float] = None
    locationRadiusMeters: Optional[float] = 200.0
    createdAt: Optional[datetime] = None
    createdBy: str  # teacher userId
    isActive: bool = True


class PeriodCreate(BaseModel):
    """For creating a new period."""
    periodNumber: int
    name: str
    startTime: str  # "HH:MM"
    endTime: str  # "HH:MM"
    dayOfWeek: int  # 0-6
    classId: str  # Class or section ID
    campusLatitude: Optional[float] = None
    campusLongitude: Optional[float] = None
    locationRadiusMeters: Optional[float] = 200.0


class PeriodUpdate(BaseModel):
    """For updating an existing period."""
    name: Optional[str] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    dayOfWeek: Optional[int] = None
    campusLatitude: Optional[float] = None
    campusLongitude: Optional[float] = None
    locationRadiusMeters: Optional[float] = None
    isActive: Optional[bool] = None


class PeriodAttendance(BaseModel):
    """Attendance record for a specific period."""
    attendanceId: str
    userId: str
    periodId: str
    classId: str
    attendanceDate: str  # "YYYY-MM-DD" in IST
    status: str  # 'present' | 'absent' | 'late'
    markedAt: Optional[datetime] = None  # When they marked attendance (IST)
    markedBy: str = 'student'  # 'student' | 'teacher_manual'


class PeriodAttendanceCreate(BaseModel):
    """For creating attendance record for a period."""
    userId: str
    periodId: str
    classId: str
    attendanceDate: str  # "YYYY-MM-DD"
    status: str = 'present'
    studentLatitude: Optional[float] = None
    studentLongitude: Optional[float] = None


class AbsentNotificationLog(BaseModel):
    """Log of absence notifications sent to students."""
    notificationId: str
    userId: str
    periodId: str
    classId: str
    attendanceDate: str
    studentEmail: str
    sentAt: datetime
    status: str  # 'sent' | 'failed'
    failureReason: Optional[str] = None
