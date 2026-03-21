from app.db.firebase_client import get_firestore
from app.models.attendance import AttendanceCreate, SpoofAttempt
from datetime import datetime
from typing import List, Dict

from google.api_core.exceptions import FailedPrecondition
from app.utils.timezone_utils import now_utc, utc_to_ist

class AttendanceService:
    def __init__(self):
        self.db = get_firestore()

    def mark_attendance(self, attendance: AttendanceCreate) -> str:
        # Check deduplication using Firestore query
        existing = self.db.collection('attendance')\
            .where('sessionId', '==', attendance.sessionId)\
            .where('userId', '==', attendance.userId)\
            .limit(1)\
            .get()

        if len(existing) > 0:
            raise ValueError("Already marked for this session")

        # Add to Firestore
        doc_ref = self.db.collection('attendance').document()
        data = {
            "recordId": doc_ref.id,
            "userId": attendance.userId,
            "sessionId": attendance.sessionId,
            "markedAt": now_utc(),
            "confidence": attendance.confidence,
            "livenessScore": attendance.livenessScore,
            "cameraId": attendance.cameraId,
            "status": attendance.status
        }
        doc_ref.set(data)

        return doc_ref.id

    def get_attendance_history(self, user_id: str = None, session_id: str = None, limit: int = 100) -> List[Dict]:
        query = self.db.collection('attendance')
        if user_id:
            actual_user_id = None

            # First, try the provided value as a direct users document id (UUID userId).
            direct_user_doc = self.db.collection('users').document(user_id).get()
            if direct_user_doc.exists:
                actual_user_id = user_id
            else:
                # Fallback: treat it as an employeeId and resolve to user document id.
                user_docs = self.db.collection('users').where('employeeId', '==', user_id).limit(1).stream()
                user_doc = next(user_docs, None)
                if user_doc:
                    actual_user_id = user_doc.id

            if not actual_user_id:
                return []

            query = query.where('userId', '==', actual_user_id)
        if session_id:
            query = query.where('sessionId', '==', session_id)

        # Firestore requires composite indexes for some query patterns (e.g. filtering + ordering).
        # To avoid requiring a Firestore index, we fetch and sort in-memory if necessary.
        try:
            docs = query.order_by('markedAt', direction='DESCENDING').limit(limit).stream()
            records = [doc.to_dict() for doc in docs]
            for record in records:
                if record.get('markedAt') is not None:
                    record['markedAt'] = utc_to_ist(record['markedAt'])
            return records
        except FailedPrecondition:
            # If Firestore demands an index, fall back to an in-memory sort.
            docs = list(query.limit(limit * 5).stream())
            records = [doc.to_dict() for doc in docs]
            records.sort(key=lambda r: r.get('markedAt') or datetime.min, reverse=True)
            records = records[:limit]
            for record in records:
                if record.get('markedAt') is not None:
                    record['markedAt'] = utc_to_ist(record['markedAt'])
            return records

    def log_spoof_attempt(self, attempt: SpoofAttempt):
        self.db.collection('spoofAttempts').add(attempt.dict())