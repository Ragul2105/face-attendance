from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import cv2
import numpy as np
from app.services.face_engine import FaceEngine
from app.services.matcher import FaceMatcher
from app.services.liveness import LivenessGate, LivenessSession
from app.services.attendance import AttendanceService
from app.config import config
from app.models.attendance import AttendanceCreate
from datetime import datetime

router = APIRouter()

def generate_frames():
    print("Starting camera stream...")

    # Instantiate services
    try:
        print("Initializing FaceEngine...")
        face_engine = FaceEngine()
        print("Initializing FaceMatcher...")
        matcher = FaceMatcher()
        print("Initializing LivenessGate...")
        liveness_gate = LivenessGate()
        print("Initializing AttendanceService...")
        attendance_service = AttendanceService()
        print("All services initialized successfully")
    except Exception as e:
        print(f"Error initializing services: {e}")
        import traceback
        traceback.print_exc()
        # Return an error frame
        error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(error_frame, "Initialization Error", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        cv2.putText(error_frame, str(e)[:50], (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        ret, buffer = cv2.imencode('.jpg', error_frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        return

    print(f"Opening camera with index: {config.CAMERA_INDEX}")
    cap = cv2.VideoCapture(int(config.CAMERA_INDEX) if config.CAMERA_INDEX.isdigit() else config.CAMERA_INDEX)

    # Check if camera opened successfully
    if not cap.isOpened():
        error_msg = f"Failed to open camera with index {config.CAMERA_INDEX}"
        print(error_msg)
        # Return an error frame
        error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(error_frame, "Camera Error", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
        cv2.putText(error_frame, "Failed to open camera", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.putText(error_frame, f"Camera Index: {config.CAMERA_INDEX}", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
        cv2.putText(error_frame, "Try changing CAMERA_INDEX in .env", (50, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        ret, buffer = cv2.imencode('.jpg', error_frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        return

    print("Camera opened successfully")
    cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)
    print(f"Camera FPS set to: {config.CAMERA_FPS}")

    session_id = datetime.now().strftime("%Y-%m-%d__morning")
    camera_id = "cam1"
    sessions = {}

    frame_count = 0
    try:
        print("Starting frame reading loop...")
        while True:
            try:
                ret, frame = cap.read()
                if not ret:
                    print("Failed to read frame from camera")
                    break

                frame_count += 1
                if frame_count % 30 == 0:  # Log every 30 frames
                    print(f"Processing frame {frame_count}...")

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

                # Encode frame for streaming
                ret, buffer = cv2.imencode('.jpg', frame)
                if not ret:
                    print("Failed to encode frame")
                    continue

                frame_bytes = buffer.tobytes()

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            except Exception as e:
                print(f"Error in frame processing loop: {e}")
                import traceback
                traceback.print_exc()
                # Continue to next frame instead of breaking
                continue

    except Exception as e:
        print(f"Fatal error in generate_frames: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Releasing camera...")
        cap.release()
        print("Camera released")

@router.get("/stream")
async def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")