from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt as pybcrypt
from passlib.context import CryptContext
from app.config import config
from app.db.firebase_client import get_firestore

router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

STAFF_ROLES = {"staff", "admin", "teacher", "employee"}


def verify_pin(plain_pin: str, pin_hash: str) -> bool:
    try:
        # Backward compatibility for previously-created bcrypt hashes.
        if pin_hash.startswith("$2"):
            return pybcrypt.checkpw(plain_pin.encode("utf-8"), pin_hash.encode("utf-8"))
        return pwd_context.verify(plain_pin, pin_hash)
    except Exception:
        return False

class LoginRequest(BaseModel):
    employeeId: str
    pin: str = None
    role: str = None

class LoginResponse(BaseModel):
    accessToken: str
    userId: str
    employeeId: str
    name: str
    role: str
    expiresAt: datetime

class UserInfo(BaseModel):
    userId: str
    employeeId: str
    name: str
    role: str

def create_access_token(user_data: dict) -> str:
    """Create JWT access token."""
    expire = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": user_data["userId"],
        "employeeId": user_data["employeeId"],
        "name": user_data["name"],
        "role": user_data["role"],
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """Verify JWT token and return user data."""
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInfo:
    """Dependency to get current authenticated user."""
    payload = verify_token(credentials.credentials)
    return UserInfo(
        userId=payload["sub"],
        employeeId=payload["employeeId"],
        name=payload["name"],
        role=payload["role"]
    )


async def require_staff_user(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
    if current_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")
    return current_user

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login endpoint for mobile app.
    Currently uses simple employeeId check.
    TODO: Add proper password/PIN authentication.
    """
    db = get_firestore()

    # Find user by employeeId (for students this can be student ID)
    users_ref = db.collection('users').where('employeeId', '==', request.employeeId).limit(1)
    docs = list(users_ref.stream())

    if not docs:
        raise HTTPException(status_code=404, detail="User not found")

    user_doc = docs[0]
    user_data = user_doc.to_dict()
    user_role = user_data.get('role', 'student')

    if not user_data.get('isActive', True):
        raise HTTPException(status_code=403, detail="User account is inactive")

    if request.role and request.role != user_role:
        raise HTTPException(status_code=403, detail=f"This account is not a {request.role} account")

    # Students can login only after full onboarding (all 10 images processed)
    if user_role == 'student' and not user_data.get('isOnboarded', False):
        raise HTTPException(status_code=403, detail="Student onboarding is not complete yet")

    # PIN verification (required only when pinHash is configured)
    pin_hash = user_data.get('pinHash')
    if pin_hash:
        if not request.pin:
            raise HTTPException(status_code=401, detail="PIN is required")
        if not verify_pin(request.pin, pin_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create access token
    token_data = {
        "userId": user_doc.id,
        "employeeId": user_data['employeeId'],
        "name": user_data['name'],
        "role": user_role
    }
    access_token = create_access_token(token_data)

    expire_time = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)

    return LoginResponse(
        accessToken=access_token,
        userId=user_doc.id,
        employeeId=user_data['employeeId'],
        name=user_data['name'],
        role=user_role,
        expiresAt=expire_time
    )

@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: UserInfo = Depends(get_current_user)):
    """Get current user information from token."""
    return current_user

@router.post("/verify-token")
async def verify_token_endpoint(current_user: UserInfo = Depends(get_current_user)):
    """Verify if token is still valid."""
    return {"valid": True, "user": current_user}
