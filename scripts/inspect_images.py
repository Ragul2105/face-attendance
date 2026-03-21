import os
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from app.services.face_engine import FaceEngine

IMAGE_DIR = Path(__file__).resolve().parent.parent / "images"

engine = FaceEngine()

print(f"Inspecting images in: {IMAGE_DIR}")

for img_path in sorted(IMAGE_DIR.glob("*.jpg")):
    img = Image.open(img_path)
    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    embedding, meta = engine.get_embedding(frame)

    print(f"\n--- {img_path.name} ---")
    if embedding is None or meta is None:
        print("No face detected")
        continue

    det_score = meta.get("det_score", None)
    bbox = meta.get("bbox", None)
    print(f"det_score={det_score}")
    print(f"bbox={bbox}")
    if bbox:
        x1, y1, x2, y2 = map(int, bbox)
        face_roi = frame[y1:y2, x1:x2]
        if face_roi.size == 0:
            print("face ROI empty")
        else:
            gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            lap = cv2.Laplacian(gray, cv2.CV_64F).var()
            print(f"face size: {face_roi.shape[:2]}, laplacian var: {lap}")

    print(f"embedding norm: {np.linalg.norm(embedding) if embedding is not None else None}")
