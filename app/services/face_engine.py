import insightface
from insightface.app import FaceAnalysis
import numpy as np
from typing import Tuple, Optional, Dict
import cv2
from app.config import config

class FaceEngine:
    MODEL_NAME = config.INSIGHTFACE_MODEL  # "buffalo_l"
    CTX_ID = 0  # 0 = GPU, -1 = CPU
    DET_SIZE = (640, 640)
    DET_THRESH = 0.5

    def __init__(self):
        self.app = FaceAnalysis(name=self.MODEL_NAME, providers=['CoreMLExecutionProvider', 'CPUExecutionProvider'])
        self.app.prepare(ctx_id=self.CTX_ID, det_size=self.DET_SIZE)

    def get_embedding(self, frame: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[Dict]]:
        """
        Returns (embedding, face_metadata) or (None, None) if no valid face detected.
        """
        faces = self.app.get(frame)
        if not faces:
            return None, None

        # Select the largest face (closest to camera)
        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

        # L2-normalize the embedding for cosine similarity
        embedding = face.embedding
        embedding = embedding / np.linalg.norm(embedding)

        meta = {
            "bbox": face.bbox.tolist(),
            "det_score": float(face.det_score),
            "age": int(face.age) if hasattr(face, "age") else None,
            "gender": face.gender if hasattr(face, "gender") else None,
        }
        return embedding, meta