from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List, Optional, Dict
import numpy as np
import cv2
import base64
import csv
from io import BytesIO
from PIL import Image
from passlib.context import CryptContext
from app.services.face_engine import FaceEngine
from app.services.matcher import FaceMatcher
from app.db.firebase_client import get_firestore
from app.api.schemas import UserRegisterRequest, UserRegisterResponse, UserResponse
from app.api.routes.auth import require_staff_user, get_current_user, UserInfo
from app.config import config
from datetime import datetime
import uuid

router = APIRouter()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

face_engine = FaceEngine()
matcher = FaceMatcher()
db = get_firestore()


def _extract_embedding_from_image(contents: bytes):
    image = Image.open(BytesIO(contents))
    frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    embedding, meta = face_engine.get_embedding(frame)
    if embedding is None or meta is None:
        raise HTTPException(status_code=422, detail="No face detected")

    det_score = meta.get('det_score', 0)
    if det_score < 0.7:
        raise HTTPException(status_code=422, detail="Low face detection confidence")

    bbox = meta.get('bbox')
    if not bbox or len(bbox) != 4:
        raise HTTPException(status_code=422, detail="Invalid face bounding box")

    x1, y1, x2, y2 = map(int, bbox)
    face_width = x2 - x1
    face_height = y2 - y1
    if face_width < config.FACE_MIN_SIZE or face_height < config.FACE_MIN_SIZE:
        raise HTTPException(status_code=422, detail="Face is too small in the image")

    face_roi = frame[y1:y2, x1:x2]
    if face_roi.size == 0:
        raise HTTPException(status_code=422, detail="Invalid face ROI")

    gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < config.BLUR_LAPLACIAN_THRESHOLD:
        raise HTTPException(status_code=422, detail="Image is too blurry")

    return embedding


def _hash_pin(pin: str) -> str:
    return pwd_context.hash(pin)


def _build_onboarding_update(user_id: str, uploaded_embeddings: Dict[str, str], image_count: int):
    update_data = {
        "uploadedEmbeddings": uploaded_embeddings,
        "uploadedImageCount": image_count,
        "lastImageUpdatedAt": datetime.utcnow(),
    }

    if image_count >= 10:
        vectors = []
        for idx in range(1, 11):
            item = uploaded_embeddings.get(str(idx))
            if not item:
                raise HTTPException(status_code=422, detail="All 10 image slots are required")
            vectors.append(np.frombuffer(base64.b64decode(item), dtype=np.float32))

        mean_embedding = np.mean(vectors, axis=0)
        mean_embedding = mean_embedding / np.linalg.norm(mean_embedding)

        duplicate = matcher.find_match(mean_embedding)
        if duplicate['matched'] and duplicate['user_id'] != user_id:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "DUPLICATE_FACE",
                    "matched_user_id": duplicate['user_id'],
                    "similarity_score": duplicate['confidence'],
                },
            )

        update_data.update(
            {
                "embedding": base64.b64encode(mean_embedding.astype(np.float32).tobytes()).decode('utf-8'),
                "embeddingDim": 512,
                "isOnboarded": True,
                "onboardedAt": datetime.utcnow(),
            }
        )

    return update_data


@router.post("/staff")
async def create_staff(
    name: str = Form(...),
    staff_id: str = Form(...),
    pin: str = Form(...),
    email: Optional[str] = Form(None),
    department: str = Form("college"),
    role: str = Form("staff"),
):
    allowed_roles = {"staff", "admin", "teacher", "employee"}
    if role not in allowed_roles:
        raise HTTPException(status_code=422, detail=f"role must be one of: {', '.join(sorted(allowed_roles))}")

    existing = list(db.collection('users').where('employeeId', '==', staff_id).limit(1).stream())
    if existing:
        raise HTTPException(status_code=409, detail="Staff ID already exists")

    user_id = str(uuid.uuid4())
    staff_data = {
        "userId": user_id,
        "employeeId": staff_id,
        "name": name,
        "department": department,
        "role": role,
        "email": email,
        "registeredAt": datetime.utcnow(),
        "isActive": True,
        "isOnboarded": True,
        "uploadedImageCount": 0,
        "embeddingDim": 0,
        "pinHash": _hash_pin(pin),
        "createdBy": "public-endpoint",
    }
    db.collection('users').document(user_id).set(staff_data)

    return {
        "userId": user_id,
        "staffId": staff_id,
        "name": name,
        "role": role,
        "message": "Staff account created successfully",
    }


@router.post("/students")
async def create_student(
    name: str = Form(...),
    student_id: str = Form(...),
    gender: str = Form(...),
    email: str = Form(...),
    pin: str = Form(...),
    department: str = Form("college"),
    current_user: UserInfo = Depends(require_staff_user),
):
    existing = list(db.collection('users').where('employeeId', '==', student_id).limit(1).stream())
    if existing:
        raise HTTPException(status_code=409, detail="Student ID already exists")

    user_id = str(uuid.uuid4())
    student_data = {
        "userId": user_id,
        "employeeId": student_id,
        "name": name,
        "department": department,
        "role": "student",
        "gender": gender,
        "email": email,
        "registeredAt": datetime.utcnow(),
        "isActive": True,
        "isOnboarded": False,
        "uploadedImageCount": 0,
        "uploadedEmbeddings": {},
        "embeddingDim": 512,
        "pinHash": _hash_pin(pin),
        "createdBy": current_user.userId,
    }
    db.collection('users').document(user_id).set(student_data)

    return {
        "userId": user_id,
        "studentId": student_id,
        "name": name,
        "isOnboarded": False,
        "uploadedImageCount": 0,
        "message": "Student created. Upload 10 images to complete onboarding.",
    }


@router.post("/students/bulk-upload")
async def bulk_create_students(
    file: UploadFile = File(...),
    default_pin: Optional[str] = Form("2026"),
    current_user: UserInfo = Depends(require_staff_user),
):
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = (await file.read()).decode('utf-8-sig')
    reader = csv.DictReader(content.splitlines())

    required_columns = {"student_name", "id", "gender", "mail_id"}
    incoming_columns = set(reader.fieldnames or [])
    if not required_columns.issubset(incoming_columns):
        raise HTTPException(
            status_code=400,
            detail=f"CSV must include columns: {', '.join(sorted(required_columns))}",
        )

    created = []
    skipped = []

    for row in reader:
        student_id = (row.get("id") or "").strip()
        name = (row.get("student_name") or "").strip()
        gender = (row.get("gender") or "").strip()
        email = (row.get("mail_id") or "").strip()

        if not student_id or not name or not gender or not email:
            skipped.append({"id": student_id or None, "reason": "Missing required values"})
            continue

        existing = list(db.collection('users').where('employeeId', '==', student_id).limit(1).stream())
        if existing:
            skipped.append({"id": student_id, "reason": "Student ID already exists"})
            continue

        user_id = str(uuid.uuid4())
        student_data = {
            "userId": user_id,
            "employeeId": student_id,
            "name": name,
            "department": "college",
            "role": "student",
            "gender": gender,
            "email": email,
            "registeredAt": datetime.utcnow(),
            "isActive": True,
            "isOnboarded": False,
            "uploadedImageCount": 0,
            "uploadedEmbeddings": {},
            "embeddingDim": 512,
            "createdBy": current_user.userId,
        }

        if default_pin:
            student_data["pinHash"] = _hash_pin(default_pin)

        db.collection('users').document(user_id).set(student_data)
        created.append({"userId": user_id, "studentId": student_id, "name": name})

    return {
        "createdCount": len(created),
        "skippedCount": len(skipped),
        "created": created,
        "skipped": skipped,
    }


@router.post("/students/{user_id}/images")
async def upload_student_image(
    user_id: str,
    image_index: int = Form(...),
    image: UploadFile = File(...),
    current_user: UserInfo = Depends(get_current_user),
):
    if image_index < 1 or image_index > 10:
        raise HTTPException(status_code=422, detail="image_index must be between 1 and 10")

    user_doc_ref = db.collection('users').document(user_id)
    user_doc = user_doc_ref.get()
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="Student not found")

    user_data = user_doc.to_dict()
    if user_data.get('role') != 'student':
        raise HTTPException(status_code=400, detail="Target user is not a student")

    # Allow upload by staff or by the same student account.
    if current_user.role == 'student' and current_user.userId != user_id:
        raise HTTPException(status_code=403, detail="You can only upload your own images")

    contents = await image.read()
    embedding = _extract_embedding_from_image(contents)
    embedding_b64 = base64.b64encode(embedding.astype(np.float32).tobytes()).decode('utf-8')

    uploaded_embeddings: Dict[str, str] = user_data.get('uploadedEmbeddings', {}) or {}
    uploaded_embeddings[str(image_index)] = embedding_b64

    image_count = len(uploaded_embeddings)
    update_data = _build_onboarding_update(user_id, uploaded_embeddings, image_count)

    user_doc_ref.update(update_data)

    if update_data.get("isOnboarded"):
        matcher.refresh_cache()

    return {
        "userId": user_id,
        "uploadedImageCount": image_count,
        "remaining": max(0, 10 - image_count),
        "isOnboarded": update_data.get("isOnboarded", user_data.get("isOnboarded", False)),
    }


@router.post("/students/{user_id}/images/bulk")
async def bulk_upload_student_images(
    user_id: str,
    images: List[UploadFile] = File(...),
    current_user: UserInfo = Depends(get_current_user),
):
    if len(images) != 10:
        raise HTTPException(status_code=422, detail="Exactly 10 images are required")

    user_doc_ref = db.collection('users').document(user_id)
    user_doc = user_doc_ref.get()
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="Student not found")

    user_data = user_doc.to_dict()
    if user_data.get('role') != 'student':
        raise HTTPException(status_code=400, detail="Target user is not a student")

    if current_user.role == 'student' and current_user.userId != user_id:
        raise HTTPException(status_code=403, detail="You can only upload your own images")

    uploaded_embeddings: Dict[str, str] = {}
    for idx, image in enumerate(images, start=1):
        contents = await image.read()
        embedding = _extract_embedding_from_image(contents)
        embedding_b64 = base64.b64encode(embedding.astype(np.float32).tobytes()).decode('utf-8')
        uploaded_embeddings[str(idx)] = embedding_b64

    image_count = len(uploaded_embeddings)
    update_data = _build_onboarding_update(user_id, uploaded_embeddings, image_count)

    user_doc_ref.update(update_data)

    if update_data.get("isOnboarded"):
        matcher.refresh_cache()

    return {
        "userId": user_id,
        "uploadedImageCount": image_count,
        "remaining": max(0, 10 - image_count),
        "isOnboarded": update_data.get("isOnboarded", user_data.get("isOnboarded", False)),
    }


@router.get("/students")
async def list_students_with_progress(
    limit: int = 200,
    current_user: UserInfo = Depends(require_staff_user),
):
    users_docs = db.collection('users').where('role', '==', 'student').limit(limit).stream()
    students = [doc.to_dict() for doc in users_docs]

    attendance_docs = list(db.collection('attendance').stream())
    total_sessions = {doc.to_dict().get('sessionId') for doc in attendance_docs if doc.to_dict().get('sessionId')}
    total_sessions_count = len(total_sessions)

    attendance_by_user = {}
    for doc in attendance_docs:
        data = doc.to_dict()
        uid = data.get('userId')
        sid = data.get('sessionId')
        if not uid or not sid:
            continue
        attendance_by_user.setdefault(uid, set()).add(sid)

    result = []
    for student in students:
        uid = student.get('userId')
        attended_sessions_count = len(attendance_by_user.get(uid, set()))
        attendance_percentage = 0.0
        if total_sessions_count > 0:
            attendance_percentage = round((attended_sessions_count / total_sessions_count) * 100, 2)

        result.append(
            {
                "userId": uid,
                "studentId": student.get('employeeId'),
                "name": student.get('name'),
                "gender": student.get('gender'),
                "email": student.get('email'),
                "isOnboarded": student.get('isOnboarded', False),
                "uploadedImageCount": student.get('uploadedImageCount', 0),
                "attendancePercentage": attendance_percentage,
                "attendedSessions": attended_sessions_count,
                "totalSessions": total_sessions_count,
                "isActive": student.get('isActive', True),
            }
        )

    return {
        "count": len(result),
        "students": result,
    }

@router.post("/register", response_model=UserRegisterResponse)
async def register_user(
    name: str = Form(...),
    employee_id: str = Form(...),
    department: str = Form(...),
    role: str = Form(...),
    frames: List[UploadFile] = File(...),
    current_user: UserInfo = Depends(require_staff_user),
):
    if len(frames) != 10:
        raise HTTPException(status_code=422, detail="Exactly 10 frames required")

    embeddings = []
    valid_frames = 0
    failed_frames = []

    for idx, frame_file in enumerate(frames, start=1):
        # Read image
        contents = await frame_file.read()
        image = Image.open(BytesIO(contents))
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Quality checks
        embedding, meta = face_engine.get_embedding(frame)
        if embedding is None or meta is None:
            failed_frames.append((idx, "no_face_detected"))
            continue

        det_score = meta.get('det_score', 0)
        if det_score < 0.7:
            failed_frames.append((idx, f"low_det_score:{det_score:.3f}"))
            continue

        # Ensure face is large enough
        bbox = meta.get('bbox')
        if not bbox or len(bbox) != 4:
            failed_frames.append((idx, "invalid_bbox"))
            continue
        x1, y1, x2, y2 = map(int, bbox)
        face_width = x2 - x1
        face_height = y2 - y1
        if face_width < config.FACE_MIN_SIZE or face_height < config.FACE_MIN_SIZE:
            failed_frames.append((idx, f"face_too_small:{face_width}x{face_height}"))
            continue

        # Blur check on face ROI
        face_roi = frame[y1:y2, x1:x2]
        if face_roi.size == 0:
            failed_frames.append((idx, "empty_face_roi"))
            continue
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < config.BLUR_LAPLACIAN_THRESHOLD:
            failed_frames.append((idx, f"too_blurry:{laplacian_var:.2f}"))
            continue

        embeddings.append(embedding)
        valid_frames += 1

    if valid_frames < 5:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "INSUFFICIENT_VALID_FRAMES",
                "valid_frames": valid_frames,
                "failed_frames": failed_frames,
            },
        )

    # Pose diversity check (placeholder: assume ok)

    # Mean embedding
    mean_embedding = np.mean(embeddings, axis=0)
    mean_embedding = mean_embedding / np.linalg.norm(mean_embedding)

    # Duplicate check
    duplicate = matcher.find_match(mean_embedding)
    if duplicate['matched']:
        raise HTTPException(status_code=409, detail={
            "error": "DUPLICATE_FACE",
            "matched_user_id": duplicate['user_id'],
            "similarity_score": duplicate['confidence']
        })

    # Generate user ID
    user_id = str(uuid.uuid4())

    # Store in Firestore (including embedding)
    user_data = {
        "userId": user_id,
        "employeeId": employee_id,
        "name": name,
        "department": department,
        "role": role,
        "isOnboarded": True,
        "uploadedImageCount": 10,
        "registeredAt": datetime.utcnow(),
        "isActive": True,
        "embeddingDim": 512,
        "embedding": base64.b64encode(mean_embedding.tobytes()).decode('utf-8'),  # Store embedding as base64
        "createdBy": current_user.userId,
    }
    db.collection('users').document(user_id).set(user_data)

    # Refresh the matcher's cache to include the new user
    matcher.refresh_cache()

    return UserRegisterResponse(
        userId=user_id,
        name=name,
        employeeId=employee_id,
        embeddingDimensions=512,
        registeredAt=user_data['registeredAt']
    )

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    doc = db.collection('users').document(user_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    data = doc.to_dict()
    return UserResponse(**data)

@router.get("/", response_model=List[UserResponse])
async def list_users(limit: int = 100, current_user: UserInfo = Depends(require_staff_user)):
    docs = db.collection('users').limit(limit).stream()
    users = []
    for doc in docs:
        users.append(UserResponse(**doc.to_dict()))
    return users

@router.delete("/{user_id}")
async def delete_user(user_id: str, current_user: UserInfo = Depends(require_staff_user)):
    # Soft delete - just mark as inactive
    db.collection('users').document(user_id).update({"isActive": False})

    # Refresh the matcher's cache to remove this user
    matcher.refresh_cache()

    return {"message": "User deactivated"}