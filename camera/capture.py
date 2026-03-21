import cv2
import numpy as np
from app.services.face_engine import FaceEngine
from app.services.matcher import FaceMatcher
from app.services.liveness import LivenessGate, LivenessSession
from app.services.attendance import AttendanceService
from app.config import config
from app.models.attendance import AttendanceCreate
from datetime import datetime

def main():
    # Instantiate services
    face_engine = FaceEngine()
    matcher = FaceMatcher()
    liveness_gate = LivenessGate()
    attendance_service = AttendanceService()

    cap = cv2.VideoCapture(int(config.CAMERA_INDEX) if config.CAMERA_INDEX.isdigit() else config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)

    session_id = datetime.now().strftime("%Y-%m-%d__morning")  # Example
    camera_id = "cam1"

    sessions = {}  # user_id -> LivenessSession 

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Detect face
        embedding, meta = face_engine.get_embedding(frame)
        if embedding is None:
            cv2.putText(frame, "No face detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        else:
            bbox = meta['bbox']
            x1, y1, x2, y2 = map(int, bbox)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Match
            match = matcher.find_match(embedding)
            user_id = match.get('user_id')
            confidence = match['confidence']

            if user_id and user_id not in sessions:
                sessions[user_id] = LivenessSession()

            session = sessions.get(user_id)
            if session:
                liveness_result = liveness_gate.evaluate(session, frame, bbox)
                if liveness_result.is_live:
                    # Mark attendance
                    try:
                        attendance_data = AttendanceCreate(
                            userId=user_id,
                            sessionId=session_id,
                            confidence=confidence,
                            livenessScore=1.0,
                            cameraId=camera_id,
                            status="present"
                        )
                        attendance_service.mark_attendance(attendance_data)
                        cv2.putText(frame, f"Attendance marked: {user_id}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    except ValueError:
                        cv2.putText(frame, f"Already marked: {user_id}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                else:
                    cv2.putText(frame, f"Liveness failed: {user_id}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            else:
                cv2.putText(frame, f"Unknown face: {confidence:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

        cv2.imshow("Face Attendance", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()