# Face Attendance Mobile App

A Flutter mobile application for the Face Recognition Attendance System.

## Features

- ✅ Employee login with Employee ID
- ✅ Capture photo with camera or gallery
- ✅ Real-time face recognition attendance marking
- ✅ View attendance history
- ✅ User profile management
- ✅ Offline-ready authentication
- ✅ Material Design 3 UI

## Prerequisites

- Flutter SDK (3.0.0 or higher)
- Android Studio / Xcode (for iOS)
- Your laptop running the FastAPI backend server

## Setup Instructions

### 1. Configure Server Connection

**IMPORTANT**: Edit `lib/config/api_config.dart` and set your laptop's IP address:

```dart
static const String baseUrl = 'http://YOUR_LAPTOP_IP:8000';
```

**How to find your laptop's IP:**
- **macOS**: System Preferences > Network > Your connection > IP Address
- **Windows**: Command Prompt > `ipconfig` > IPv4 Address
- **Linux**: Terminal > `ip addr show` or `ifconfig`

Example: If your IP is `192.168.1.100`, set:
```dart
static const String baseUrl = 'http://192.168.1.100:8000';
```

### 2. Start the Backend Server

On your laptop, make sure the API server is running:

```bash
cd /path/to/face_attendance
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Note**: Use `--host 0.0.0.0` to allow connections from your mobile device!

### 3. Connect to Same Network

Ensure your phone and laptop are on the **SAME WiFi network**.

### 4. Install Flutter Dependencies

```bash
cd mobile_app
flutter pub get
```

### 5. Run the App

**For Android:**
```bash
flutter run
```

**For iOS:**
```bash
flutter run
```

**Or select device in VS Code/Android Studio and press Run.**

## Testing Connection

1. Open your phone's browser
2. Go to `http://YOUR_LAPTOP_IP:8000/docs`
3. If you see the API documentation, you're connected!

## Usage

### Login
1. Enter your Employee ID (must be registered in the system)
2. Tap "Sign In"

### Mark Attendance
1. Go to "Mark" tab
2. Tap "Take Photo" or "Choose from Gallery"
3. Capture a clear photo of your face
4. Tap "Mark Attendance"
5. Wait for confirmation

### View History
1. Go to "History" tab
2. Pull down to refresh
3. See all your attendance records

## Troubleshooting

### "Server offline" error
- Check if backend server is running
- Verify laptop IP address in `api_config.dart`
- Ensure phone and laptop are on same WiFi
- Try pinging your laptop: `ping YOUR_LAPTOP_IP`

### "No face detected"
- Ensure good lighting
- Face should be clearly visible
- Hold camera steady
- Remove glasses/masks if possible

### "Face not recognized"
- Make sure you're registered in the system
- Face must be registered via the web interface first
- Check confidence threshold settings

### Permission Issues (Android)
- Grant camera permission when prompted
- Settings > Apps > Face Attendance > Permissions

### Permission Issues (iOS)
- Grant camera & photo library access when prompted
- Settings > Face Attendance > Allow Camera Access

## Building for Release

### Android APK
```bash
flutter build apk --release
```
Output: `build/app/outputs/flutter-apk/app-release.apk`

### iOS IPA
```bash
flutter build ios --release
```

## Project Structure

```
mobile_app/
├── lib/
│   ├── main.dart                 # App entry point
│   ├── config/
│   │   └── api_config.dart       # Server configuration
│   ├── models/
│   │   └── models.dart           # Data models
│   ├── services/
│   │   ├── auth_service.dart     # Authentication
│   │   └── api_service.dart      # API client
│   └── screens/
│       ├── login_screen.dart     # Login UI
│       ├── home_screen.dart      # Main navigation
│       ├── camera_screen.dart    # Attendance marking
│       ├── history_screen.dart   # Attendance history
│       └── profile_screen.dart   # User profile
└── pubspec.yaml                  # Dependencies
```

## License

Copyright © 2024. All rights reserved.
