from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# User schemas
class UserRegisterRequest(BaseModel):
    name: str
    employeeId: str
    department: str
    role: str  # 'student' | 'employee' | 'teacher' | 'admin'

class UserRegisterResponse(BaseModel):
    userId: str
    name: str
    employeeId: str
    embeddingDimensions: int
    registeredAt: datetime

class UserResponse(BaseModel):
    userId: str
    employeeId: str
    name: str
    department: str
    role: str
    registeredAt: datetime
    isActive: bool
    embeddingDim: int

# Attendance schemas
class MarkAttendanceRequest(BaseModel):
    image: str  # base64 encoded image
    cameraId: str
    sessionId: str

class MarkAttendanceResponse(BaseModel):
    success: bool
    userId: Optional[str]
    confidence: float
    status: str
    message: str

class AttendanceRecordResponse(BaseModel):
    recordId: str
    userId: str
    sessionId: str
    markedAt: datetime
    confidence: float
    livenessScore: float
    cameraId: str
    status: str

# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str