import numpy as np
import cv2
from scipy.spatial import distance
from skimage.feature import local_binary_pattern
import hashlib
from typing import Dict, List, Optional, Tuple
from app.db.firebase_client import get_firestore
from datetime import datetime, timedelta

# Constants
EAR_THRESHOLD = 0.25
BLINK_FRAMES = 3
BLINK_REQUIRED = 2
LBP_RADIUS = 1
LBP_POINTS = 8 * LBP_RADIUS
TEXTURE_THRESHOLD = 8.0
MOVEMENT_THRESHOLD = 0.5

class LivenessSession:
    def __init__(self):
        self.blink_count = 0
        self.eye_closed_frames = 0
        self.lbp_variance = 0.0
        self.mean_displacement = 0.0
        self.landmarks_history: List[List[Tuple[float, float]]] = []
        self.frames: List[np.ndarray] = []

    def add_frame(self, frame: np.ndarray, bbox: List[float]):
        self.frames.append(frame)
        # Extract face ROI
        x1, y1, x2, y2 = map(int, bbox)
        face_roi = frame[y1:y2, x1:x2]
        if face_roi.size == 0:
            return
        # Compute LBP
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        lbp = local_binary_pattern(gray, LBP_POINTS, LBP_RADIUS, method='uniform')
        self.lbp_variance = np.var(lbp)

        if len(self.frames) > 10:
            self.frames.pop(0)
            self.landmarks_history.pop(0)

    def detect_blink(self, landmarks: List[Tuple[float, float]]) -> bool:
        # Left eye indices in MediaPipe: 33, 160, 158, 133, 153, 144
        left_indices = [33, 160, 158, 133, 153, 144]
        right_indices = [362, 385, 387, 263, 373, 380]

        if len(landmarks) < 468:
            return False

        left_eye = [landmarks[i] for i in left_indices]
        right_eye = [landmarks[i] for i in right_indices]

        left_ear = self.compute_ear(left_eye)
        right_ear = self.compute_ear(right_eye)
        ear = (left_ear + right_ear) / 2.0

        if ear < EAR_THRESHOLD:
            self.eye_closed_frames += 1
        else:
            if self.eye_closed_frames >= BLINK_FRAMES:
                self.blink_count += 1
            self.eye_closed_frames = 0

        return self.blink_count >= BLINK_REQUIRED

    def compute_ear(self, eye_landmarks: List[Tuple[float, float]]) -> float:
        A = distance.euclidean(eye_landmarks[1], eye_landmarks[5])
        B = distance.euclidean(eye_landmarks[2], eye_landmarks[4])
        C = distance.euclidean(eye_landmarks[0], eye_landmarks[3])
        return (A + B) / (2.0 * C)

    def compute_movement(self) -> float:
        if len(self.landmarks_history) < 2:
            return 0.0
        displacements = []
        for i in range(1, len(self.landmarks_history)):
            prev = np.array(self.landmarks_history[i-1])
            curr = np.array(self.landmarks_history[i])
            disp = np.mean(np.linalg.norm(curr - prev, axis=1))
            displacements.append(disp)
        return np.mean(displacements) if displacements else 0.0

class LivenessResult:
    def __init__(self, is_live: bool, details: Dict):
        self.is_live = is_live
        self.details = details

class LivenessGate:
    def __init__(self):
        # Temporarily disable mediapipe due to import issues
        # self.mp_face_mesh = mp.solutions.face_mesh
        # self.face_mesh = self.mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)
        self.db = get_firestore()

    def evaluate(self, session: LivenessSession, frame: np.ndarray, bbox: List[float]) -> LivenessResult:
        # Temporary: always return live for testing
        # TODO: Implement proper liveness detection
        results = {
            "blink_passed": True,
            "texture_passed": True,
            "movement_passed": True,
        }
        all_passed = True
        return LivenessResult(is_live=all_passed, details=results)

    def log_spoof_attempt(self, camera_id: str, reason: str, frame: np.ndarray):
        snapshot_hash = hashlib.sha256(frame.tobytes()).hexdigest()
        attempt_data = {
            "attemptedAt": datetime.utcnow(),
            "failureReason": reason,
            "cameraId": camera_id,
            "snapshotHash": snapshot_hash
        }
        self.db.collection('spoofAttempts').add(attempt_data)

        # Rate limiting using Firestore - count attempts in last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_attempts = self.db.collection('spoofAttempts')\
            .where('cameraId', '==', camera_id)\
            .where('attemptedAt', '>=', one_hour_ago)\
            .get()

        if len(recent_attempts) > 5:
            # Alert admin, placeholder
            print(f"Alert: High spoof attempts on camera {camera_id} ({len(recent_attempts)} in last hour)")