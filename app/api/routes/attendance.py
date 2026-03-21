from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import numpy as np
import cv2
import base64
from io import BytesIO
from PIL import Image
from app.services.face_engine import FaceEngine
from app.services.matcher import FaceMatcher
from app.services.liveness import LivenessGate, LivenessSession
from app.services.attendance import AttendanceService
from app.api.schemas import MarkAttendanceRequest, MarkAttendanceResponse, AttendanceRecordResponse
from app.config import config
from app.models.attendance import AttendanceCreate

router = APIRouter()

# Instantiate inside functions to avoid module-level issues
# face_engine = FaceEngine()
# matcher = FaceMatcher()
# liveness_gate = LivenessGate()
# attendance_service = AttendanceService()

@router.post("/mark", response_model=MarkAttendanceResponse)
async def mark_attendance(request: MarkAttendanceRequest):
    # Instantiate services
    face_engine = FaceEngine()
    matcher = FaceMatcher()
    liveness_gate = LivenessGate()
    attendance_service = AttendanceService()

    # Decode image
    try:
        image_data = base64.b64decode(request.image)
        image = Image.open(BytesIO(image_data))
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    except:
        raise HTTPException(status_code=400, detail="Invalid image")

    # Get embedding
    embedding, meta = face_engine.get_embedding(frame)
    if embedding is None:
        return MarkAttendanceResponse(
            success=False,
            userId=None,
            confidence=0.0,
            status="NO_FACE",
            message="No face detected"
        )

    # Liveness check
    session = LivenessSession()
    liveness_result = liveness_gate.evaluate(session, frame, meta['bbox'])
    if not liveness_result.is_live:
        # Log spoof
        liveness_gate.log_spoof_attempt(request.cameraId, "LIVENESS_FAILED", frame)
        return MarkAttendanceResponse(
            success=False,
            userId=None,
            confidence=0.0,
            status="SPOOF_DETECTED",
            message=f"Liveness failed: {liveness_result.details}"
        )

    # Match
    match = matcher.find_match(embedding)
    if not match['matched']:
        return MarkAttendanceResponse(
            success=False,
            userId=None,
            confidence=match['confidence'],
            status=match.get('status', 'UNKNOWN'),
            message="No match found"
        )

    # Mark attendance
    try:
        attendance_data = AttendanceCreate(
            userId=match['user_id'],
            sessionId=request.sessionId,
            confidence=match['confidence'],
            livenessScore=1.0 if liveness_result.is_live else 0.0,
            cameraId=request.cameraId,
            status="present"
        )
        record_id = attendance_service.mark_attendance(attendance_data)
        return MarkAttendanceResponse(
            success=True,
            userId=match['user_id'],
            confidence=match['confidence'],
            status="ATTENDANCE_MARKED",
            message=f"Attendance marked for user {match['user_id']}"
        )
    except ValueError as e:
        return MarkAttendanceResponse(
            success=False,
            userId=match['user_id'],
            confidence=match['confidence'],
            status="ALREADY_MARKED",
            message=str(e)
        )

@router.get("/", response_model=List[AttendanceRecordResponse])
async def get_attendance(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 100
):
    attendance_service = AttendanceService()
    records = attendance_service.get_attendance_history(user_id, session_id, limit)
    return [AttendanceRecordResponse(**rec) for rec in records]

@router.get("/user/{user_id}", response_model=List[AttendanceRecordResponse])
async def get_user_attendance(user_id: str, limit: int = 100):
    attendance_service = AttendanceService()
    records = attendance_service.get_attendance_history(user_id=user_id, limit=limit)
    return [AttendanceRecordResponse(**rec) for rec in records]