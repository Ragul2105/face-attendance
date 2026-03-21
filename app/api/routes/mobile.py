from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Optional
import numpy as np
import cv2
from io import BytesIO
from PIL import Image
from app.services.face_engine import FaceEngine
from app.services.matcher import FaceMatcher
from app.services.liveness import LivenessGate, LivenessSession
from app.services.attendance import AttendanceService
from app.api.routes.auth import get_current_user, UserInfo, verify_pin
from app.models.attendance import AttendanceCreate
from app.config import config
from datetime import datetime
from pydantic import BaseModel
from app.utils.timezone_utils import now_ist

router = APIRouter()

class MobileAttendanceResponse(BaseModel):
    success: bool
    userId: Optional[str] = None
    userName: Optional[str] = None
    employeeId: Optional[str] = None
    confidence: float = 0.0
    status: str
    message: str
    markedAt: Optional[datetime] = None

@router.post("/mark-mobile", response_model=MobileAttendanceResponse)
async def mark_attendance_mobile(
    image: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    camera_id: str = Form("mobile"),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Mobile-friendly attendance marking endpoint.
    Accepts image file upload instead of base64.
    """
    # Instantiate services
    face_engine = FaceEngine()
    matcher = FaceMatcher()
    liveness_gate = LivenessGate()
    attendance_service = AttendanceService()

    # Default session_id for mobile (daily)
    if not session_id:
        session_id = now_ist().strftime("%Y-%m-%d")

    # Read and process image
    try:
        contents = await image.read()
        pil_image = Image.open(BytesIO(contents))
        frame = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")

    # Get embedding
    embedding, meta = face_engine.get_embedding(frame)
    if embedding is None:
        return MobileAttendanceResponse(
            success=False,
            status="NO_FACE",
            message="No face detected in the image. Please try again with a clear face photo."
        )

    # Liveness check (simplified for mobile)
    session = LivenessSession()
    liveness_result = liveness_gate.evaluate(session, frame, meta['bbox'])
    if not liveness_result.is_live:
        liveness_gate.log_spoof_attempt(camera_id, "LIVENESS_FAILED", frame)
        return MobileAttendanceResponse(
            success=False,
            status="SPOOF_DETECTED",
            message="Liveness check failed. Please take a live photo."
        )

    # Match face
    match = matcher.find_match(embedding)
    if not match['matched']:
        return MobileAttendanceResponse(
            success=False,
            confidence=match['confidence'],
            status=match.get('status', 'UNKNOWN'),
            message="Face not recognized. Please ensure you're registered in the system."
        )

    # Get user details from Firestore
    from app.db.firebase_client import get_firestore
    db = get_firestore()
    user_doc = db.collection('users').document(match['user_id']).get()

    if not user_doc.exists:
        return MobileAttendanceResponse(
            success=False,
            userId=match['user_id'],
            confidence=match['confidence'],
            status="USER_NOT_FOUND",
            message="User record not found in database."
        )

    user_data = user_doc.to_dict()

    # Mark attendance
    try:
        attendance_data = AttendanceCreate(
            userId=match['user_id'],
            sessionId=session_id,
            confidence=match['confidence'],
            livenessScore=1.0 if liveness_result.is_live else 0.0,
            cameraId=camera_id,
            status="present"
        )
        record_id = attendance_service.mark_attendance(attendance_data)

        return MobileAttendanceResponse(
            success=True,
            userId=match['user_id'],
            userName=user_data.get('name'),
            employeeId=user_data.get('employeeId'),
            confidence=match['confidence'],
            status="ATTENDANCE_MARKED",
            message=f"Attendance marked successfully for {user_data.get('name')}",
            markedAt=now_ist()
        )
    except ValueError as e:
        return MobileAttendanceResponse(
            success=False,
            userId=match['user_id'],
            userName=user_data.get('name'),
            employeeId=user_data.get('employeeId'),
            confidence=match['confidence'],
            status="ALREADY_MARKED",
            message=f"Attendance already marked today for {user_data.get('name')}"
        )


@router.post("/mark-mobile-pin", response_model=MobileAttendanceResponse)
async def mark_attendance_mobile_pin(
    employee_id: str = Form(...),
    pin: str = Form(...),
    camera_id: str = Form("mobile"),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    PIN-based attendance marking endpoint (fallback when face detection fails).
    Accepts employee_id and PIN to mark attendance.
    """
    attendance_service = AttendanceService()

    # Default session_id for mobile (daily)
    session_id = now_ist().strftime("%Y-%m-%d")

    # Get Firestore database
    from app.db.firebase_client import get_firestore
    db = get_firestore()

    # Find user by employee ID
    user_query = list(db.collection('users').where('employeeId', '==', employee_id).limit(1).stream())
    
    if not user_query:
        return MobileAttendanceResponse(
            success=False,
            status="USER_NOT_FOUND",
            message=f"No student found with ID: {employee_id}"
        )

    user_doc = user_query[0]
    user_id = user_doc.id
    user_data = user_doc.to_dict()

    # Check if user is a student
    if user_data.get('role') != 'student':
        return MobileAttendanceResponse(
            success=False,
            status="INVALID_USER",
            message="Only students can mark attendance with PIN."
        )

    # Verify PIN
    pin_hash = user_data.get('pinHash')
    if not pin_hash:
        return MobileAttendanceResponse(
            success=False,
            userId=user_id,
            userName=user_data.get('name'),
            employeeId=employee_id,
            status="NO_PIN_SET",
            message="PIN not set for this student. Please contact administrator."
        )

    if not verify_pin(pin, pin_hash):
        return MobileAttendanceResponse(
            success=False,
            userId=user_id,
            userName=user_data.get('name'),
            employeeId=employee_id,
            status="INVALID_PIN",
            message="Incorrect PIN. Please try again."
        )

    # Mark attendance
    try:
        attendance_data = AttendanceCreate(
            userId=user_id,
            sessionId=session_id,
            confidence=1.0,  # PIN-verified (100% confidence)
            livenessScore=0.0,  # No liveness check for PIN-based
            cameraId=camera_id,
            status="present"
        )
        record_id = attendance_service.mark_attendance(attendance_data)

        return MobileAttendanceResponse(
            success=True,
            userId=user_id,
            userName=user_data.get('name'),
            employeeId=employee_id,
            confidence=1.0,
            status="ATTENDANCE_MARKED",
            message=f"Attendance marked successfully for {user_data.get('name')} via PIN",
            markedAt=now_ist()
        )
    except ValueError as e:
        return MobileAttendanceResponse(
            success=False,
            userId=user_id,
            userName=user_data.get('name'),
            employeeId=employee_id,
            confidence=1.0,
            status="ALREADY_MARKED",
            message=f"Attendance already marked today for {user_data.get('name')}"
        )
