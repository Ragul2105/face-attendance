from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AttendanceRecord(BaseModel):
    recordId: str
    userId: str
    sessionId: str  # Format: YYYY-MM-DD__{shiftOrClass}
    markedAt: datetime
    confidence: float
    livenessScore: float
    cameraId: str
    status: str  # 'present' | 'late' | 'absent'

class AttendanceCreate(BaseModel):
    userId: str
    sessionId: str
    confidence: float
    livenessScore: float
    cameraId: str
    status: str = "present"

class SpoofAttempt(BaseModel):
    attemptId: str
    attemptedAt: datetime
    failureReason: str  # 'NO_BLINK' | 'FLAT_TEXTURE' | 'NO_MOVEMENT' | 'LOW_CONFIDENCE'
    cameraId: str
    snapshotHash: str