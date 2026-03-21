from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class User(BaseModel):
    userId: str
    employeeId: str
    name: str
    department: str
    role: str  # 'student' | 'employee' | 'teacher' | 'admin'
    registeredAt: datetime
    isActive: bool = True
    embeddingDim: int = 512
    embeddingRef: str

class UserCreate(BaseModel):
    name: str
    employeeId: str
    department: str
    role: str

class UserResponse(BaseModel):
    userId: str
    employeeId: str
    name: str
    department: str
    role: str
    registeredAt: datetime
    isActive: bool
    embeddingDim: int