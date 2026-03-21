#!/usr/bin/env python3
"""
Comprehensive test for period attendance marking and email flow.
Tests:
1. Period creation
2. Attendance marking during window
3. Attendance marking outside window (should fail on backend)
4. Scheduler checking for absent students
5. Email notification logging
"""

import os
import sys
import requests
import json
from datetime import datetime, timedelta
from pytz import timezone
import time

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.firebase_client import get_firestore
from app.services.period_scheduler import PeriodSchedulerService
from app.utils.timezone_utils import now_ist

BASE_URL = "http://127.0.0.1:8000"
IST = timezone('Asia/Kolkata')

def show(step, result):
    """Print formatted test results."""
    print(f"\n{'='*60}")
    print(f"✓ {step}")
    print(f"{'='*60}")
    if isinstance(result, dict):
        print(json.dumps(result, indent=2))
    else:
        print(result)

def main():
    print("\n" + "="*60)
    print("FULL PERIOD ATTENDANCE FLOW TEST")
    print("="*60)
    
    db = get_firestore()
    
    # 1. Create test period (TODAY, but starting 2 hours ago and ending 1 hour ago)
    now = now_ist()
    today_str = now.strftime("%Y-%m-%d")
    day_of_week = now.weekday()
    
    # Create a period that ENDED 1 hour ago (for scheduler testing)
    start_hour = (now.hour - 2) % 24
    end_hour = (now.hour - 1) % 24
    start_time = f"{start_hour:02d}:00"
    end_time = f"{end_hour:02d}:00"
    
    period_data = {
        "periodId": f"test_period_{now.strftime('%H%M%S')}",
        "classId": "college",
        "periodNumber": 99,
        "name": "Test Period (Ended)",
        "startTime": start_time,
        "endTime": end_time,
        "dayOfWeek": day_of_week,
        "createdAt": now,
        "createdBy": "teacher_test",
        "isActive": True,
    }
    db.collection("periods").document(period_data["periodId"]).set(period_data)
    show("PERIOD_CREATED", {
        "periodId": period_data["periodId"],
        "class": period_data["classId"],
        "timeWindow": f"{start_time} - {end_time} IST",
        "dayOfWeek": day_of_week,
    })
    
    # 2. Try to mark attendance OUTSIDE window (this should fail on backend)
    print("\n\nTEST 1: Try to mark attendance OUTSIDE period window")
    print("-" * 60)
    
    # Create test credentials if needed
    teacher_login = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={"staff_id": "teacher_test", "pin": "1234"},
        timeout=10,
    )
    show("TEACHER_LOGIN", teacher_login.status_code)
    teacher_token = teacher_login.json().get("accessToken")
    
    student_login = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={"student_id": "student_test", "pin": "1234"},
        timeout=10,
    )
    show("STUDENT_LOGIN", student_login.status_code)
    student_token = student_login.json().get("accessToken")
    student_id = student_login.json().get("userId")
    
    # Try marking OUTSIDE window
    mark_response = requests.post(
        f"{BASE_URL}/api/v1/periods/attendance/period",
        headers={"Authorization": f"Bearer {student_token}"},
        data={
            "periodId": period_data["periodId"],
            "classId": period_data["classId"],
            "attendanceDate": today_str,
            "status": "present",
        },
        timeout=10,
    )
    show("MARK_OUTSIDE_WINDOW", {
        "status_code": mark_response.status_code,
        "message": mark_response.text if mark_response.status_code != 200 else "SUCCESS (unexpected!)",
    })
    
    # 3. Test scheduler to check if it marks absent and sends emails
    print("\n\nTEST 2: Run scheduler to process ended periods")
    print("-" * 60)
    
    try:
        scheduler = PeriodSchedulerService()
        result = scheduler.run_period_end_checks()
        show("SCHEDULER_RUN", result)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Check notification logs
    print("\n\nTEST 3: Check absence notification logs")
    print("-" * 60)
    
    notifications = list(db.collection("absenceNotifications").stream())
    show("NOTIFICATION_LOGS", {
        "totalNotifications": len(notifications),
        "latestNotifications": [
            {
                "studentEmail": doc.to_dict().get("studentEmail"),
                "status": doc.to_dict().get("status"),
                "sentAt": doc.to_dict().get("sentAt"),
            }
            for doc in notifications[-5:]
        ]
    })
    
    # 5. Check period attendance records
    print("\n\nTEST 4: Check period attendance records")
    print("-" * 60)
    
    attendances = list(
        db.collection("periodAttendance")
        .where("periodId", "==", period_data["periodId"])
        .stream()
    )
    show("PERIOD_ATTENDANCE", {
        "periodId": period_data["periodId"],
        "totalRecords": len(attendances),
        "records": [
            {
                "userId": doc.to_dict().get("userId"),
                "status": doc.to_dict().get("status"),
                "markedAt": doc.to_dict().get("markedAt"),
                "markedBy": doc.to_dict().get("markedBy"),
            }
            for doc in attendances
        ]
    })
    
    # 6. Try marking SAME PERIOD again (should get "already marked" error)
    print("\n\nTEST 5: Try marking attendance again (should fail with 409)")
    print("-" * 60)
    
    # First, create a period that IS happening NOW
    now_period_data = {
        "periodId": f"test_period_now_{now.strftime('%H%M%S')}",
        "classId": "college",
        "periodNumber": 98,
        "name": "Test Period (Now)",
        "startTime": now.strftime("%H:%M"),
        "endTime": f"{(now.hour+1) % 24:02d}:00",
        "dayOfWeek": day_of_week,
        "createdAt": now,
        "createdBy": "teacher_test",
        "isActive": True,
    }
    db.collection("periods").document(now_period_data["periodId"]).set(now_period_data)
    
    # Mark attendance first time
    mark1 = requests.post(
        f"{BASE_URL}/api/v1/periods/attendance/period",
        headers={"Authorization": f"Bearer {student_token}"},
        data={
            "periodId": now_period_data["periodId"],
            "classId": now_period_data["classId"],
            "attendanceDate": today_str,
            "status": "present",
        },
        timeout=10,
    )
    show("MARK_FIRST_TIME", {
        "status_code": mark1.status_code,
        "response": mark1.json() if mark1.status_code == 200 else mark1.text,
    })
    
    # Try marking same period again
    mark2 = requests.post(
        f"{BASE_URL}/api/v1/periods/attendance/period",
        headers={"Authorization": f"Bearer {student_token}"},
        data={
            "periodId": now_period_data["periodId"],
            "classId": now_period_data["classId"],
            "attendanceDate": today_str,
            "status": "present",
        },
        timeout=10,
    )
    show("MARK_SECOND_TIME (should be 409)", {
        "status_code": mark2.status_code,
        "response": mark2.text,
    })
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
