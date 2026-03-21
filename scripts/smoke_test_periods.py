import uuid
from datetime import datetime, timedelta

import requests
from passlib.context import CryptContext

from app.db.firebase_client import get_firestore
from app.services.period_scheduler import PeriodSchedulerService

BASE = "http://127.0.0.1:8000"
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
db = get_firestore()


def show(label, value):
    print(f"{label}: {value}")


def seed_student(class_id: str, student_pin: str, emp_id: str, name: str, email: str) -> str:
    user_id = str(uuid.uuid4())
    db.collection("users").document(user_id).set(
        {
            "userId": user_id,
            "employeeId": emp_id,
            "name": name,
            "department": "college",
            "classId": class_id,
            "role": "student",
            "gender": "other",
            "email": email,
            "registeredAt": datetime.utcnow(),
            "isActive": True,
            "isOnboarded": True,
            "uploadedImageCount": 10,
            "uploadedEmbeddings": {},
            "embeddingDim": 512,
            "pinHash": pwd_context.hash(student_pin),
            "createdBy": "smoke-test",
        }
    )
    return user_id


def main():
    created_user_ids = []
    created_period_id = None
    created_class_id = None

    health = requests.get(f"{BASE}/api/v1/health", timeout=10)
    show("HEALTH", (health.status_code, health.json().get("status")))

    suffix = uuid.uuid4().hex[:6]
    class_id = f"class_{suffix}"
    created_class_id = class_id
    teacher_staff_id = f"TCHR{suffix}"
    student_present_id = f"STUP{suffix}"
    student_absent_id = f"STUA{suffix}"

    teacher_pin = "2026"
    student_pin = "2026"

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    weekday = now.weekday()
    start_time = (now - timedelta(hours=1)).strftime("%H:%M")
    end_time = (now - timedelta(minutes=1)).strftime("%H:%M")

    create_teacher = requests.post(
        f"{BASE}/api/v1/users/staff",
        data={
            "name": f"Teacher {suffix}",
            "staff_id": teacher_staff_id,
            "pin": teacher_pin,
            "role": "teacher",
            "department": "college",
            "email": f"teacher_{suffix}@example.com",
        },
        timeout=15,
    )
    show("CREATE_TEACHER", (create_teacher.status_code, create_teacher.text[:120]))

    teacher_login = requests.post(
        f"{BASE}/api/v1/auth/login",
        json={"employeeId": teacher_staff_id, "role": "teacher", "pin": teacher_pin},
        timeout=15,
    )
    if teacher_login.status_code != 200:
        raise SystemExit(f"Teacher login failed: {teacher_login.status_code} {teacher_login.text}")
    teacher_token = teacher_login.json()["accessToken"]
    show("TEACHER_LOGIN", teacher_login.status_code)

    create_period = requests.post(
        f"{BASE}/api/v1/periods/periods",
        headers={"Authorization": f"Bearer {teacher_token}"},
        data={
            "periodNumber": "1",
            "name": f"Period-{suffix}",
            "startTime": start_time,
            "endTime": end_time,
            "dayOfWeek": str(weekday),
            "classId": class_id,
        },
        timeout=15,
    )
    if create_period.status_code != 200:
        raise SystemExit(f"Create period failed: {create_period.status_code} {create_period.text}")
    period_id = create_period.json()["periodId"]
    created_period_id = period_id
    show("CREATE_PERIOD", (create_period.status_code, period_id))

    present_uid = seed_student(
        class_id,
        student_pin,
        student_present_id,
        f"Present {suffix}",
        f"present_{suffix}@example.com",
    )
    absent_uid = seed_student(
        class_id,
        student_pin,
        student_absent_id,
        f"Absent {suffix}",
        f"absent_{suffix}@example.com",
    )
    show("SEEDED_STUDENTS", {"present": present_uid, "absent": absent_uid, "classId": class_id})
    created_user_ids.extend([present_uid, absent_uid])

    student_login = requests.post(
        f"{BASE}/api/v1/auth/login",
        json={"employeeId": student_present_id, "role": "student", "pin": student_pin},
        timeout=15,
    )
    if student_login.status_code != 200:
        raise SystemExit(f"Student login failed: {student_login.status_code} {student_login.text}")
    student_token = student_login.json()["accessToken"]
    show("STUDENT_LOGIN", student_login.status_code)

    mark = requests.post(
        f"{BASE}/api/v1/periods/attendance/period",
        headers={"Authorization": f"Bearer {student_token}"},
        data={
            "periodId": period_id,
            "classId": class_id,
            "attendanceDate": today,
            "status": "present",
        },
        timeout=15,
    )
    if mark.status_code != 200:
        raise SystemExit(f"Mark attendance failed: {mark.status_code} {mark.text}")
    show("MARK_ATTENDANCE", (mark.status_code, mark.json().get("status")))

    scheduler = PeriodSchedulerService()
    scheduler_result = scheduler.run_period_end_checks()
    show("SCHEDULER_RESULT", scheduler_result)

    absent_docs = list(
        db.collection("periodAttendance")
        .where("userId", "==", absent_uid)
        .where("periodId", "==", period_id)
        .where("attendanceDate", "==", today)
        .stream()
    )
    show("ABSENT_RECORDS", {"count": len(absent_docs), "statuses": [d.to_dict().get("status") for d in absent_docs]})

    notif_docs = list(
        db.collection("absenceNotifications")
        .where("userId", "==", absent_uid)
        .where("periodId", "==", period_id)
        .where("attendanceDate", "==", today)
        .stream()
    )
    show(
        "NOTIFICATIONS",
        {
            "count": len(notif_docs),
            "rows": [
                {
                    "status": d.to_dict().get("status"),
                    "email": d.to_dict().get("studentEmail"),
                }
                for d in notif_docs
            ],
        },
    )

    print("SMOKE_TEST_DONE")

    # Cleanup smoke test records to avoid polluting production-like data.
    cleanup_smoke_test_data(
        class_id=created_class_id,
        period_id=created_period_id,
        user_ids=created_user_ids,
        suffix=suffix,
    )


def cleanup_smoke_test_data(class_id: str, period_id: str, user_ids: list, suffix: str) -> None:
    if not class_id or not period_id:
        return

    # Delete period attendance for this period/class
    attendance_docs = list(
        db.collection("periodAttendance")
        .where("periodId", "==", period_id)
        .stream()
    )
    for doc in attendance_docs:
        doc.reference.delete()

    # Delete notifications for this period
    notif_docs = list(
        db.collection("absenceNotifications")
        .where("periodId", "==", period_id)
        .stream()
    )
    for doc in notif_docs:
        doc.reference.delete()

    # Delete scheduler run logs for this period
    run_docs = list(
        db.collection("periodSchedulerRuns")
        .where("periodId", "==", period_id)
        .stream()
    )
    for doc in run_docs:
        doc.reference.delete()

    # Delete created users and teacher by known IDs/pattern
    for uid in user_ids:
        db.collection("users").document(uid).delete()

    teacher_docs = list(
        db.collection("users")
        .where("employeeId", "==", f"TCHR{suffix}")
        .stream()
    )
    for doc in teacher_docs:
        doc.reference.delete()

    # Delete period
    db.collection("periods").document(period_id).delete()
    show("CLEANUP", {"classId": class_id, "periodId": period_id, "usersDeleted": len(user_ids) + len(teacher_docs)})


if __name__ == "__main__":
    main()
