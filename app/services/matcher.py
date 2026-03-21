import numpy as np
from app.db.firebase_client import get_firestore
from app.config import config

class FaceMatcher:
    MATCH_THRESHOLD = config.MATCH_THRESHOLD  # 0.65
    UNKNOWN_THRESHOLD = 0.50

    def __init__(self):
        self.db = get_firestore()
        self._embedding_cache = {}  # Cache embeddings in memory for performance
        self._load_embeddings()

    def _load_embeddings(self):
        """Load all user embeddings from Firestore into memory cache."""
        try:
            users_ref = self.db.collection('users').where('isActive', '==', True)
            docs = users_ref.stream()

            for doc in docs:
                user_data = doc.to_dict()
                if 'embedding' in user_data:
                    # Convert base64 or bytes back to numpy array
                    embedding_bytes = user_data['embedding']
                    if isinstance(embedding_bytes, str):
                        import base64
                        embedding_bytes = base64.b64decode(embedding_bytes)
                    embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                    self._embedding_cache[doc.id] = embedding
        except Exception as e:
            print(f"Warning: Could not load embeddings from Firestore: {e}")
            # Continue with empty cache - will return no matches

    def refresh_cache(self):
        """Refresh the embedding cache from Firestore."""
        self._embedding_cache = {}
        self._load_embeddings()

    def find_match(self, query_embedding: np.ndarray) -> dict:
        """Compare query embedding against all stored embeddings."""
        best_match = None
        best_score = -1.0

        # Search through cached embeddings
        for user_id, stored_embedding in self._embedding_cache.items():
            score = float(np.dot(query_embedding, stored_embedding))  # both L2-normed

            if score > best_score:
                best_score = score
                best_match = user_id

        if best_score >= self.MATCH_THRESHOLD:
            return {"matched": True, "user_id": best_match, "confidence": best_score}
        elif best_score >= self.UNKNOWN_THRESHOLD:
            return {"matched": False, "user_id": None, "confidence": best_score, "status": "LOW_CONFIDENCE"}
        else:
            return {"matched": False, "user_id": None, "confidence": best_score, "status": "UNKNOWN"}