import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Firebase
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_SERVICE_ACCOUNT_JSON: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")

    # InsightFace
    INSIGHTFACE_MODEL: str = os.getenv("INSIGHTFACE_MODEL", "buffalo_l")
    MATCH_THRESHOLD: float = float(os.getenv("MATCH_THRESHOLD", "0.65"))
    LIVENESS_REQUIRED: bool = os.getenv("LIVENESS_REQUIRED", "true").lower() == "true"

    # Camera
    CAMERA_INDEX: str = os.getenv("CAMERA_INDEX", "0")
    CAMERA_FPS: int = int(os.getenv("CAMERA_FPS", "15"))

    # Quality thresholds
    FACE_MIN_SIZE: int = int(os.getenv("FACE_MIN_SIZE", "120"))
    BLUR_LAPLACIAN_THRESHOLD: float = float(os.getenv("BLUR_LAPLACIAN_THRESHOLD", "3.0"))

    # API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # Data Retention
    ATTENDANCE_RETENTION_DAYS: int = int(os.getenv("ATTENDANCE_RETENTION_DAYS", "1095"))

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

    # Timezone
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Kolkata")

    # Email/SMTP
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "")
    SENDER_PASSWORD: str = os.getenv("SENDER_PASSWORD", "")
    SENDER_NAME: str = os.getenv("SENDER_NAME", "Face Attendance System")

config = Config()