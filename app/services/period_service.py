"""
Service for managing periods and period-based attendance.
"""

import uuid
import math
from datetime import datetime
from typing import List, Dict, Optional

from app.db.firebase_client import get_firestore
from app.models.period import Period, PeriodCreate, PeriodAttendance, PeriodAttendanceCreate
from app.utils.timezone_utils import now_ist, utc_to_ist, ist_to_utc, now_utc


class PeriodService:
    """Service for managing class periods and period-based attendance."""

    def __init__(self):
        self.db = get_firestore()

    # ==================== PERIOD MANAGEMENT ====================

    def create_period(self, period_create: PeriodCreate, teacher_id: str) -> Period:
        """Create a new period."""
        period_id = f"period_{uuid.uuid4().hex[:12]}"
        
        period_data = {
            "periodId": period_id,
            "classId": period_create.classId,
            "periodNumber": period_create.periodNumber,
            "name": period_create.name,
            "startTime": period_create.startTime,
            "endTime": period_create.endTime,
            "dayOfWeek": period_create.dayOfWeek,
            "campusLatitude": period_create.campusLatitude,
            "campusLongitude": period_create.campusLongitude,
            "locationRadiusMeters": period_create.locationRadiusMeters or 200.0,
            "createdAt": now_utc(),  # Store as UTC
            "createdBy": teacher_id,
            "isActive": True,
        }

        self.db.collection("periods").document(period_id).set(period_data)
        
        period_data["createdAt"] = utc_to_ist(period_data["createdAt"])
        return Period(**period_data)

    def get_periods_for_class(self, class_id: str, day_of_week: Optional[int] = None) -> List[Period]:
        """
        Get all periods for a class.
        
        Args:
            class_id: Class ID
            day_of_week: Optional day (0-6). If provided, filter to that day.
        
        Returns:
            List of Period objects
        """
        query = self.db.collection("periods").where("classId", "==", class_id).where("isActive", "==", True)
        
        docs = query.stream()
        periods = []
        
        for doc in docs:
            data = doc.to_dict()
            if day_of_week is not None and data.get("dayOfWeek") != day_of_week:
                continue
            
            data["createdAt"] = utc_to_ist(data["createdAt"])
            periods.append(Period(**data))
        
        # Sort by period number and start time
        periods.sort(key=lambda p: (p.periodNumber, p.startTime))
        return periods

    def get_period(self, period_id: str) -> Optional[Period]:
        """Get a specific period."""
        doc = self.db.collection("periods").document(period_id).get()
        
        if not doc.exists:
            return None
        
        data = doc.to_dict()
        data["createdAt"] = utc_to_ist(data["createdAt"])
        return Period(**data)

    def update_period(self, period_id: str, updates: Dict) -> Optional[Period]:
        """Update a period."""
        self.db.collection("periods").document(period_id).update(updates)
        return self.get_period(period_id)

    def deactivate_period(self, period_id: str) -> bool:
        """Deactivate a period."""
        self.db.collection("periods").document(period_id).update({"isActive": False})
        return True

    # ==================== PERIOD ATTENDANCE ====================

    def mark_period_attendance(
        self,
        attendance_create: PeriodAttendanceCreate,
        student_id: str = None,
        enforce_period_window: bool = True,
        marked_by: str = "student",
    ) -> PeriodAttendance:
        """
        Mark attendance for a specific period.
        
        Args:
            attendance_create: Attendance data
            student_id: Override userId if provided (for teacher manual marking)
        
        Returns:
            PeriodAttendance object
        """
        if enforce_period_window:
            self._validate_period_mark_window(attendance_create)

        if marked_by == "student" and attendance_create.status == "present":
            self._validate_student_location(attendance_create)

        # Check if already marked for this period on this date
        existing = list(
            self.db.collection("periodAttendance")
            .where("userId", "==", attendance_create.userId)
            .where("periodId", "==", attendance_create.periodId)
            .where("attendanceDate", "==", attendance_create.attendanceDate)
            .limit(1)
            .stream()
        )

        if existing:
            raise ValueError("Attendance already marked for this period on this date")

        attendance_id = f"pattend_{uuid.uuid4().hex[:12]}"
        
        attendance_data = {
            "attendanceId": attendance_id,
            "userId": attendance_create.userId,
            "periodId": attendance_create.periodId,
            "classId": attendance_create.classId,
            "attendanceDate": attendance_create.attendanceDate,
            "status": attendance_create.status,
            "markedAt": now_utc(),
            "markedBy": marked_by,
            "studentLatitude": attendance_create.studentLatitude,
            "studentLongitude": attendance_create.studentLongitude,
        }

        self.db.collection("periodAttendance").document(attendance_id).set(attendance_data)
        
        attendance_data["markedAt"] = utc_to_ist(attendance_data["markedAt"])
        return PeriodAttendance(**attendance_data)

    def get_attendance_for_student(
        self, user_id: str, start_date: str = None, end_date: str = None
    ) -> List[PeriodAttendance]:
        """Get period attendance records for a student."""
        query = self.db.collection("periodAttendance").where("userId", "==", user_id)
        
        docs = query.stream()
        records = []
        
        for doc in docs:
            data = doc.to_dict()
            data["markedAt"] = utc_to_ist(data["markedAt"])
            records.append(PeriodAttendance(**data))
        
        return records

    def get_attendance_for_period(self, period_id: str, attendance_date: str) -> List[Dict]:
        """Get all attendance records for a period on a specific date."""
        query = self.db.collection("periodAttendance").where(
            "periodId", "==", period_id
        ).where("attendanceDate", "==", attendance_date)
        
        docs = query.stream()
        records = []
        
        for doc in docs:
            data = doc.to_dict()
            data["markedAt"] = utc_to_ist(data["markedAt"])
            records.append(data)
        
        return records

    def get_absent_students_for_period(
        self, period_id: str, class_id: str, attendance_date: str
    ) -> List[Dict]:
        """
        Get students who were absent for a period.
        This queries students who haven't marked attendance yet.
        """
        class_students = self._get_students_for_class(class_id)

        # Get students who marked attendance for this period
        attendance_records = list(
            self.db.collection("periodAttendance")
            .where("periodId", "==", period_id)
            .where("attendanceDate", "==", attendance_date)
            .stream()
        )

        attended_user_ids = {record.to_dict()["userId"] for record in attendance_records}

        # Find absent students
        absent_students = []
        for student_doc in class_students:
            student_data = student_doc.to_dict()
            if student_data["userId"] not in attended_user_ids:
                absent_students.append(
                    {
                        "userId": student_data["userId"],
                        "name": student_data.get("name"),
                        "email": student_data.get("email"),
                        "employeeId": student_data.get("employeeId"),
                    }
                )

        return absent_students

    def mark_bulk_absent(self, period_id: str, class_id: str, attendance_date: str) -> Dict:
        """Mark all absent students for a period."""
        absent_students = self.get_absent_students_for_period(period_id, class_id, attendance_date)

        marked_count = 0
        for student in absent_students:
            try:
                attendance_create = PeriodAttendanceCreate(
                    userId=student["userId"],
                    periodId=period_id,
                    classId=class_id,
                    attendanceDate=attendance_date,
                    status="absent",
                )
                self.mark_period_attendance(
                    attendance_create,
                    enforce_period_window=False,
                    marked_by="teacher_manual",
                )
                marked_count += 1
            except ValueError:
                # Already marked, skip
                pass

        return {"total_absent": len(absent_students), "marked": marked_count}

    # ==================== STATISTICS ====================

    def get_attendance_summary(self, class_id: str, student_id: str, start_date: str = None, end_date: str = None) -> Dict:
        """Get attendance summary for a student."""
        query = self.db.collection("periodAttendance").where("userId", "==", student_id).where(
            "classId", "==", class_id
        )

        docs = query.stream()
        records = [doc.to_dict() for doc in docs]

        total = len(records)
        present = len([r for r in records if r.get("status") == "present"])
        absent = len([r for r in records if r.get("status") == "absent"])
        
        percentage = round((present / total * 100), 2) if total > 0 else 0

        return {
            "total": total,
            "present": present,
            "absent": absent,
            "percentage": percentage,
        }

    def _validate_period_mark_window(self, attendance_create: PeriodAttendanceCreate) -> None:
        """Validate period exists and is valid (not enforcing strict time windows)."""
        period = self.get_period(attendance_create.periodId)
        if not period:
            raise ValueError("Period not found")

        if not period.isActive:
            raise ValueError("This period is inactive")

        if period.classId != attendance_create.classId:
            raise ValueError("Invalid class for this period")

        # Allow marking anytime for flexibility
        # The scheduler still tracks who marked vs who didn't for absence detection

    def _validate_student_location(self, attendance_create: PeriodAttendanceCreate) -> None:
        period = self.get_period(attendance_create.periodId)
        if not period:
            raise ValueError("Period not found")

        if period.campusLatitude is None or period.campusLongitude is None:
            return

        if attendance_create.studentLatitude is None or attendance_create.studentLongitude is None:
            raise ValueError("Location is required to mark attendance for this period")

        radius_meters = period.locationRadiusMeters or 200.0
        distance_meters = self._haversine_distance_meters(
            attendance_create.studentLatitude,
            attendance_create.studentLongitude,
            period.campusLatitude,
            period.campusLongitude,
        )

        if distance_meters > radius_meters:
            raise ValueError(
                f"You are too far from campus location ({int(distance_meters)}m). Allowed radius is {int(radius_meters)}m"
            )

    def _haversine_distance_meters(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        radius_earth_m = 6371000.0

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return radius_earth_m * c

    def _time_to_minutes(self, hhmm: str) -> int:
        parts = hhmm.split(":")
        if len(parts) != 2:
            raise ValueError("Invalid period time format")
        hour = int(parts[0])
        minute = int(parts[1])
        return hour * 60 + minute

    def _get_students_for_class(self, class_id: str) -> List:
        """
        Match students by either:
        - users.classId (new schema), or
        - users.department (existing schema used in student creation)
        """
        by_class_id = list(
            self.db.collection("users")
            .where("classId", "==", class_id)
            .where("role", "==", "student")
            .where("isActive", "==", True)
            .stream()
        )
        by_department = list(
            self.db.collection("users")
            .where("department", "==", class_id)
            .where("role", "==", "student")
            .where("isActive", "==", True)
            .stream()
        )

        unique = {}
        for doc in by_class_id + by_department:
            data = doc.to_dict()
            user_id = data.get("userId")
            if user_id:
                unique[user_id] = doc

        return list(unique.values())
