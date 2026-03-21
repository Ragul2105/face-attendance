"""
Camera Diagnostic Tool
Run this script to test which camera index works on your system.
"""
import cv2
import sys

def test_camera(index):
    """Test if a camera can be opened at the given index."""
    print(f"\nTesting camera index {index}...")
    cap = cv2.VideoCapture(index)

    if not cap.isOpened():
        print(f"  ❌ Failed to open camera at index {index}")
        return False

    # Try to read a frame
    ret, frame = cap.read()
    if not ret or frame is None:
        print(f"  ❌ Camera opened but failed to read frame at index {index}")
        cap.release()
        return False

    # Get camera properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"  ✅ Camera at index {index} is working!")
    print(f"     Resolution: {width}x{height}")
    print(f"     FPS: {fps}")

    cap.release()
    return True

def main():
    print("="*60)
    print("Camera Diagnostic Tool for Face Attendance System")
    print("="*60)

    # Test camera indices 0-5
    working_cameras = []
    for i in range(6):
        if test_camera(i):
            working_cameras.append(i)

    print("\n" + "="*60)
    if working_cameras:
        print(f"✅ Found {len(working_cameras)} working camera(s): {working_cameras}")
        print(f"\nRecommendation:")
        print(f"  Update CAMERA_INDEX in your .env file to: {working_cameras[0]}")
    else:
        print("❌ No working cameras found.")
        print("\nPossible issues:")
        print("  1. Camera permissions not granted (macOS: System Preferences > Security & Privacy > Camera)")
        print("  2. Camera is being used by another application")
        print("  3. No camera connected to the system")
        print("  4. OpenCV not properly installed")

    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDiagnostic interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error during diagnostic: {e}")
        sys.exit(1)
