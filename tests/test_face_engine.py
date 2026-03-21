import pytest
import numpy as np
from app.services.face_engine import FaceEngine

def test_get_embedding():
    engine = FaceEngine()
    # Create a dummy frame (this is placeholder, need real image)
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    embedding, meta = engine.get_embedding(frame)
    if embedding is not None:
        assert len(embedding) == 512
        assert np.isclose(np.linalg.norm(embedding), 1.0)
    else:
        assert meta is None