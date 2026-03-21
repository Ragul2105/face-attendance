"""
Background scheduler for period end processing:
- mark absentees for ended periods
- send absence notification emails once per student/period/date
"""

from datetime import datetime
from typing import Dict, List
import logging

from app.db.firebase_client import get_firestore
from app.services.email_service import EmailService
from app.services.period_service import PeriodService
from app.utils.timezone_utils import now_ist


logger = logging.getLogger(__name__)


class PeriodSchedulerService:
    def __init__(self):
        self.db = get_firestore()
        self.period_service = PeriodService()
        self.email_service = EmailService()

    def run_period_end_checks(self) -> Dict[str, int]:
        """
        Process all periods that have ended today (IST):
        1) mark absent records for students who did not mark attendance
        2) send absence emails once per student/period/date
        """
        now = now_ist()
        today_str = now.strftime("%Y-%m-%d")
        day_of_week = now.weekday()  # Monday=0 ... Sunday=6
        current_time = now.strftime("%H:%M")

        periods = self._get_elapsed_periods_for_today(day_of_week, current_time)
        logger.info(
            "Scheduler tick | ist_now=%s day_of_week=%s elapsed_periods=%s",
            now.isoformat(),
            day_of_week,
            len(periods),
        )

        processed_periods = 0
        total_absent_marked = 0
        total_emails_sent = 0

        for period in periods:
            period_id = period.get("periodId")
            class_id = period.get("classId")
            period_name = period.get("name", "Period")

            if not period_id or not class_id:
                logger.warning("Skipping period with missing id/class: %s", period)
                continue

            if self._period_already_processed(period_id, today_str):
                logger.info(
                    "Skipping already processed period | period_id=%s date=%s",
                    period_id,
                    today_str,
                )
                continue

            # Capture absentees first (students who did not mark attendance yet).
            absent_students = self.period_service.get_absent_students_for_period(
                period_id, class_id, today_str
            )
            logger.info(
                "Processing ended period | period_id=%s class_id=%s absent_candidates=%s",
                period_id,
                class_id,
                len(absent_students),
            )

            # Mark absentees
            mark_result = self.period_service.mark_bulk_absent(period_id, class_id, today_str)
            total_absent_marked += mark_result.get("marked", 0)

            # Send emails to absentees (exactly once)
            emails_sent_for_period = 0
            for student in absent_students:
                user_id = student.get("userId")
                email = student.get("email")
                name = student.get("name", "Student")

                if not user_id or not email:
                    continue

                if self._notification_already_sent(user_id, period_id, today_str):
                    continue

                sent = self.email_service.send_absence_notification(
                    student_email=email,
                    student_name=name,
                    period_name=period_name,
                    class_name=class_id,
                    absence_date=today_str,
                )
                logger.info(
                    "Email attempt | period_id=%s user_id=%s email=%s sent=%s",
                    period_id,
                    user_id,
                    email,
                    sent,
                )

                self._log_notification(user_id, period_id, class_id, today_str, email, sent)
                if sent:
                    total_emails_sent += 1
                    emails_sent_for_period += 1

            self._mark_period_processed(
                period_id=period_id,
                class_id=class_id,
                attendance_date=today_str,
                absent_marked=mark_result.get("marked", 0),
                emails_sent_for_period=emails_sent_for_period,
            )
            logger.info(
                "Period processed | period_id=%s absent_marked=%s emails_sent=%s",
                period_id,
                mark_result.get("marked", 0),
                emails_sent_for_period,
            )

            processed_periods += 1

        return {
            "processed_periods": processed_periods,
            "absent_marked": total_absent_marked,
            "emails_sent": total_emails_sent,
        }

    def _get_elapsed_periods_for_today(self, day_of_week: int, current_time: str) -> List[Dict]:
        """Return active periods for today whose end time is <= current IST time."""
        query = (
            self.db.collection("periods")
            .where("isActive", "==", True)
            .where("dayOfWeek", "==", day_of_week)
        )

        elapsed = []
        for doc in query.stream():
            data = doc.to_dict()
            end_time = data.get("endTime")
            if isinstance(end_time, str) and end_time <= current_time:
                elapsed.append(data)
        return elapsed

    def _notification_already_sent(self, user_id: str, period_id: str, attendance_date: str) -> bool:
        existing = list(
            self.db.collection("absenceNotifications")
            .where("userId", "==", user_id)
            .where("periodId", "==", period_id)
            .where("attendanceDate", "==", attendance_date)
            .where("status", "==", "sent")
            .limit(1)
            .stream()
        )
        return len(existing) > 0

    def _period_already_processed(self, period_id: str, attendance_date: str) -> bool:
        run_id = f"run_{period_id}_{attendance_date}".replace("/", "-")
        doc = self.db.collection("periodSchedulerRuns").document(run_id).get()
        return doc.exists

    def _mark_period_processed(
        self,
        period_id: str,
        class_id: str,
        attendance_date: str,
        absent_marked: int,
        emails_sent_for_period: int,
    ) -> None:
        run_id = f"run_{period_id}_{attendance_date}".replace("/", "-")
        payload = {
            "runId": run_id,
            "periodId": period_id,
            "classId": class_id,
            "attendanceDate": attendance_date,
            "processedAt": now_ist(),
            "absentMarked": absent_marked,
            "emailsAttempted": emails_sent_for_period,
            "status": "completed",
        }
        self.db.collection("periodSchedulerRuns").document(run_id).set(payload)

    def _log_notification(
        self,
        user_id: str,
        period_id: str,
        class_id: str,
        attendance_date: str,
        student_email: str,
        sent: bool,
    ) -> None:
        notification_id = f"notif_{user_id}_{period_id}_{attendance_date}".replace("/", "-")
        payload = {
            "notificationId": notification_id,
            "userId": user_id,
            "periodId": period_id,
            "classId": class_id,
            "attendanceDate": attendance_date,
            "studentEmail": student_email,
            "sentAt": now_ist(),
            "status": "sent" if sent else "failed",
            "failureReason": None if sent else "smtp_send_failed",
        }
        self.db.collection("absenceNotifications").document(notification_id).set(payload)
