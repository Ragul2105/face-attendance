# Face Recognition Attendance System (FRAS)

A real-time, offline-capable face attendance system using InsightFace (ArcFace) with high accuracy and anti-spoofing. Includes backend REST API, Streamlit dashboard, and complete Flutter mobile app for iOS & Android.

---

## 🎯 Overview

**FRAS** is an enterprise-grade attendance management system with:
- 99%+ accuracy face recognition with anti-spoofing
- Geolocation-based attendance validation (200m campus radius enforcement)
- Automated period-end processing with timezone normalization (IST)
- SMS/email absence notifications
- Complete Flutter mobile app for both students and staff
- Offline-capable operation
- Period-based attendance management with staff control

---

## 🌟 Key Features

### Core System
- ✅ Real-time face recognition (99%+ accuracy)
- ✅ 3-layer liveness detection (blink, texture, movement)
- ✅ Offline operation (no cloud AI APIs required)
- ✅ Firebase Firestore backend
- ✅ REST API with JWT authentication
- ✅ Automatic period-end processing & absence marking
- ✅ IST timezone normalization across all operations
- ✅ Email notifications for absences

### Mobile App (Flutter)
- ✅ Employee ID login with JWT authentication
- ✅ Real-time camera-based attendance marking
- ✅ GPS-based location verification (200m campus radius)
- ✅ Attendance history with IST timestamp display
- ✅ Period management for staff/teachers
- ✅ Student batch upload for staff
- ✅ Pull-to-refresh and offline-first architecture
- ✅ Persistent authentication across app restarts

### Location-Based Enforcement
- ✅ Staff captures campus location (GPS) during period creation
- ✅ Students must be within 200m radius to mark attendance
- ✅ Haversine formula for accurate distance calculation
- ✅ Location data stored for audit trail

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Face Engine** | InsightFace ArcFace (buffalo_l model) |
| **Liveness Detection** | MediaPipe Face Mesh |
| **Matching Algorithm** | Cosine similarity with in-memory caching |
| **Database** | Firebase Firestore |
| **Backend API** | FastAPI (Python 3.13) |
| **Scheduler** | APScheduler (1-min interval) |
| **Web Dashboard** | Streamlit |
| **Mobile** | Flutter 3.0+ (iOS & Android) |
| **Mobile Location** | Geolocator 12.0.0 |
| **Email** | SMTP (Gmail) |

---

## ⚙️ Backend Setup

### Prerequisites
- Python 3.13+
- Firebase project with Firestore enabled
- Google Cloud service account JSON
- Gmail SMTP credentials (for notifications)

### Installation

```bash
# 1. Clone/setup project
cd face_attendance

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Then edit .env with:
#   - FIREBASE_PROJECT_ID
#   - FIREBASE_SERVICE_ACCOUNT_JSON (path to JSON file)
#   - SMTP credentials (Gmail app password)
#   - Any other API configuration
```

### Running Backend Services

#### API Server (Required for mobile app)
```bash
# For mobile app access, MUST use --host 0.0.0.0
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Note:** Using `--host 0.0.0.0` allows mobile devices on the same network to connect. Do NOT use `localhost` for mobile.

#### Streamlit Dashboard
```bash
cd dashboard
streamlit run app.py
```

#### Camera Capture Utility
```bash
python camera/capture.py
```

---

## 📱 Mobile App Setup

### Prerequisites
- Flutter SDK 3.0.0+ ([install](https://flutter.dev/docs/get-started/install))
- Android Studio or Xcode
- Physical device or emulator
- iPhone/iPad (for iOS) or Android phone/emulator
- Same WiFi network as backend server

### Quick Start (5 Steps)

#### Step 1: Find Your Laptop's IP Address

**macOS/Linux:**
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

**Windows:**
```bash
ipconfig | findstr IPv4
```

Look for IP like `192.168.1.100`

#### Step 2: Configure Mobile App (Recommended)

Pass API URL at runtime (no source-code edits required):

```bash
cd mobile_app
flutter run --dart-define=API_BASE_URL=http://192.168.1.100:8000
```

Optional fallback: if you do not pass `--dart-define`, app uses `mobile_app/lib/config/api_config.dart` default value.

#### Step 3: Start Backend Server

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Step 4: Test Connection from Phone

1. Open phone browser
2. Visit: `http://<YOUR_LAPTOP_IP>:8000/docs`
3. Should see Swagger API documentation
4. If fails: check WiFi, IP address, and firewall

#### Step 5: Run Flutter App

```bash
cd mobile_app
flutter pub get
flutter run --dart-define=API_BASE_URL=http://<YOUR_LAPTOP_IP>:8000
```

Or use automated setup:
```bash
./setup_mobile.sh
```

---

## 🔌 API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login with employee ID
- `POST /api/v1/auth/verify-token` - Verify JWT token validity
- `GET /api/v1/auth/me` - Get current authenticated user

### Users
- `POST /api/v1/users/register` - Register user with 10 face images
- `GET /api/v1/users/{user_id}` - Get specific user details
- `GET /api/v1/users/` - List all users
- `DELETE /api/v1/users/{user_id}` - Deactivate user account

### Attendance & Periods
- `POST /api/v1/attendance/mark` - Mark attendance from base64 image
- `POST /api/v1/mobile/mark-mobile` - Mark attendance from file upload (mobile)
- `GET /api/v1/attendance/` - Query attendance records
- `GET /api/v1/attendance/user/{user_id}` - Get user attendance history
- `POST /api/v1/periods/` - Create period (staff only)
- `GET /api/v1/periods/` - Get periods for today
- `POST /api/v1/periods/{period_id}/mark` - Mark period attendance with GPS validation

### Camera
- `GET /api/v1/camera/stream` - Live camera stream

---

## 📋 Common Commands

### Backend
```bash
# Activate virtual environment
source .venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Run API with full logging
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run smoke tests
PYTHONPATH=. python scripts/smoke_test_periods.py

# Clean test data
python scripts/cleanup_smoke_test_data.py
```

### Flutter Mobile
```bash
# Check Flutter installation
flutter doctor

# Install dependencies
flutter pub get

# Run on connected device
flutter run

# Build for production
flutter build apk --release  # Android
flutter build ios --release  # iOS

# View real-time logs
flutter logs

# Hot reload while running (press 'r' in terminal)
```

---

## 📁 Project Structure

```
face_attendance/
├── app/
│   ├── main.py                  # FastAPI entry point
│   ├── config.py                # Configuration
│   ├── api/
│   │   ├── routes/              # API endpoints
│   │   │   ├── auth.py
│   │   │   ├── attendance.py
│   │   │   ├── periods.py
│   │   │   ├── mobile.py
│   │   │   └── users.py
│   │   └── schemas.py           # Request/response schemas
│   ├── db/
│   │   └── firebase_client.py   # Firestore client
│   ├── models/
│   │   ├── user.py
│   │   ├── period.py
│   │   └── attendance.py
│   └── services/
│       ├── face_engine.py       # InsightFace integration
│       ├── matcher.py           # Face matching logic
│       ├── attendance.py        # Attendance business logic
│       ├── period_service.py    # Period & location validation
│       ├── period_scheduler.py  # Auto period-end processing
│       └── email_service.py     # SMTP notifications
├── mobile_app/                  # Flutter app
│   ├── lib/
│   │   ├── main.dart
│   │   ├── config/              # API configuration
│   │   ├── services/            # API & Auth services
│   │   ├── models/              # Data models
│   │   └── screens/             # UI screens
│   ├── android/
│   ├── ios/
│   └── pubspec.yaml
├── dashboard/                   # Streamlit admin UI
├── camera/                      # Camera capture utilities
├── scripts/
│   ├── smoke_test_periods.py
│   └── cleanup_smoke_test_data.py
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── docker-compose.yml
└── Dockerfile
```

---

## 🔐 Environment Configuration

Create `.env` file in project root:

```env
# Firebase
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_SERVICE_ACCOUNT_JSON=./firebase-service-account.json

# Email Notifications
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password  # Use Gmail App Password, NOT your password

# JWT
JWT_SECRET_KEY=your_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Location
DEFAULT_LOCATION_RADIUS_METERS=200

# Timezone
TIMEZONE=Asia/Kolkata  # IST
```

**IMPORTANT:** For Gmail SMTP:
1. Enable 2-Factor Authentication on Gmail account
2. Generate [App Password](https://myaccount.google.com/apppasswords)
3. Use 16-character app password in `SENDER_PASSWORD`

---

## 🚀 Deployment

### Docker
```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f
```

### Manual Deployment
1. Set up Python environment on server
2. Install dependencies: `pip install -r requirements.txt`
3. Configure `.env` with production values
4. Run API: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
5. Configure reverse proxy (nginx) for SSL/TLS

---

## 🐛 Troubleshooting

### Mobile App Can't Connect to Backend
```bash
# 1. Verify backend is running
curl http://YOUR_IP:8000/api/v1/health

# 2. Check IP in mobile_app/lib/config/api_config.dart
# It should match: ipconfig (Windows) or ifconfig (macOS/Linux)

# 3. Check firewall allows port 8000
# macOS: System Preferences > Security & Privacy > Firewall
# linux: sudo ufw allow 8000

# 4. Ensure both devices on same WiFi network
# Test with: ping YOUR_LAPTOP_IP from phone
```

### No Logs Appearing in Console
- Backend logs configured globally in `app/main.py` with INFO level
- Check that PYTHONPATH is set: `PYTHONPATH=. uvicorn app.main:app`
- View real-time logs for scheduled tasks in console output

### Location Permission Errors (Mobile)
- Android: Verify permissions in `mobile_app/android/app/src/main/AndroidManifest.xml`
- iOS: Verify descriptions in `mobile_app/ios/Runner/Info.plist`
- Grant permissions when prompted by app on first run

### SMTP Email Sending Fails
- Verify Gmail App Password (not your account password)
- Check 2FA is enabled on Gmail account
- Verify SENDER_EMAIL matches Gmail account
- Test with: Check scheduler logs show "Email attempt" in console

---

## 📊 System Architecture

**Backend Flow:**
1. Mobile app posts image + GPS to `/api/v1/mobile/mark-mobile`
2. FastAPI validates location (Haversine formula vs. campus radius)
3. FaceEngine extracts face embedding (InsightFace)
4. Matcher compares with registered embeddings (cosine similarity)
5. On match: attendance marked in Firestore, success response returned
6. Scheduler runs every minute: checks ended periods, marks absent, sends emails (IST)

**Mobile Flow:**
1. Student/staff logs in with employee ID (JWT token)
2. Staff creates period with GPS-captured campus location + 200m radius
3. Student initiates period mark → camera capture → GPS location capture
4. Image + location sent to backend
5. Backend validates: location within radius + face match
6. Result returns to app; screen reloads from backend on success
7. History shows all marked periods with IST timestamps

---

## 📞 Support

For issues or feature requests, check:
- Backend error logs: Console output when server running
- Mobile logs: `flutter logs` while app running
- API docs: `http://localhost:8000/docs` (Swagger)
- Firebase Console: Check Firestore collection structure

---

## 📄 License

[Your License Here]
- ✅ Attendance marking
- ✅ History viewing
- ✅ User profile
- ✅ Offline-ready auth

### Documentation
See [MOBILE_SETUP_GUIDE.md](MOBILE_SETUP_GUIDE.md) for complete setup instructions.

## Docker

```bash
docker-compose up
```

## Testing

Run tests:
```bash
pytest
```

## Security

- No raw images stored
- Liveness detection prevents spoofing
- JWT authentication for admin endpoints