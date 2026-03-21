"""
Dependency Check Script
Verifies all required services are running before starting the camera stream.
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def check_firebase():
    """Check if Firebase credentials are available."""
    print("\n🔍 Checking Firebase...")
    try:
        from app.config import config

        if not config.FIREBASE_SERVICE_ACCOUNT_JSON:
            print("  ⚠️  FIREBASE_SERVICE_ACCOUNT_JSON not set in .env")
            return False

        if not os.path.exists(config.FIREBASE_SERVICE_ACCOUNT_JSON):
            print(f"  ❌ Firebase credentials file not found: {config.FIREBASE_SERVICE_ACCOUNT_JSON}")
            return False

        print(f"  ✅ Firebase credentials file exists: {config.FIREBASE_SERVICE_ACCOUNT_JSON}")

        # Try to initialize Firebase
        from app.db.firebase_client import get_firestore
        db = get_firestore()
        print(f"  ✅ Firebase initialized successfully (Project: {config.FIREBASE_PROJECT_ID})")
        return True
    except Exception as e:
        print(f"  ❌ Firebase initialization failed: {e}")
        return False

def check_insightface():
    """Check if InsightFace models are available."""
    print("\n🔍 Checking InsightFace models...")
    try:
        from app.config import config
        print(f"  Model: {config.INSIGHTFACE_MODEL}")

        from app.services.face_engine import FaceEngine
        print("  Loading FaceEngine (this may take a minute on first run)...")
        engine = FaceEngine()
        print("  ✅ FaceEngine initialized successfully")
        return True
    except Exception as e:
        print(f"  ❌ FaceEngine initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_camera():
    """Check if camera is accessible."""
    print("\n🔍 Checking camera...")
    try:
        import cv2
        from app.config import config

        print(f"  Camera index: {config.CAMERA_INDEX}")
        cap = cv2.VideoCapture(int(config.CAMERA_INDEX) if config.CAMERA_INDEX.isdigit() else config.CAMERA_INDEX)

        if not cap.isOpened():
            print(f"  ❌ Cannot open camera at index {config.CAMERA_INDEX}")
            return False

        ret, frame = cap.read()
        cap.release()

        if not ret:
            print("  ❌ Camera opened but cannot read frames")
            return False

        print("  ✅ Camera is accessible and working")
        return True
    except Exception as e:
        print(f"  ❌ Camera check failed: {e}")
        return False

def main():
    print("="*70)
    print("Face Attendance System - Dependency Check")
    print("="*70)

    results = {
        "Firebase": check_firebase(),
        "InsightFace": check_insightface(),
        "Camera": check_camera()
    }

    print("\n" + "="*70)
    print("Summary:")
    print("="*70)

    all_passed = True
    for service, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {service:.<20} {status}")
        if not passed:
            all_passed = False

    print("="*70)

    if all_passed:
        print("\n🎉 All dependencies are ready!")
        print("You can now start the camera stream.")
        return 0
    else:
        print("\n⚠️  Some dependencies are not ready.")
        print("Please fix the issues above before starting the camera stream.")
        print("\nCommon fixes:")
        print("  • Firebase: Check that firebase-service-account.json path is correct in .env")
        print("  • Camera: Check camera permissions in System Preferences > Security & Privacy")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nCheck interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
