/// API Configuration for Face Attendance App
///
/// IMPORTANT: Configure your laptop's local IP address here
///
/// To find your laptop's IP:
/// - macOS: System Preferences > Network > Your connection > IP Address
/// - Windows: cmd > ipconfig > IPv4 Address
/// - Linux: terminal > ip addr show or ifconfig
///
/// Example: If your laptop IP is 192.168.1.100, set:
/// static const String baseUrl = 'http://192.168.1.100:8000';

class ApiConfig {
  /// Base URL of your FastAPI server
  ///
  /// CHANGE THIS to your laptop's IP address!
  /// Format: http://YOUR_LAPTOP_IP:8000
  ///
  /// Examples:
  /// - http://192.168.1.100:8000  (typical home network)
  /// - http://10.0.0.100:8000     (typical office network)
  /// - http://172.20.10.2:8000    (iOS hotspot)
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://172.16.125.3:8000',
  );

  // API Endpoints
  static const String loginEndpoint = '/api/v1/auth/login';
  static const String verifyTokenEndpoint = '/api/v1/auth/verify-token';
  static const String markAttendanceEndpoint = '/api/v1/mobile/mark-mobile';
  static const String markAttendancePinEndpoint =
      '/api/v1/mobile/mark-mobile-pin';
  static const String attendanceHistoryEndpoint = '/api/v1/attendance/user';
  static const String studentsEndpoint = '/api/v1/users/students';
  static const String staffEndpoint = '/api/v1/users/staff';
  static const String periodsBaseEndpoint = '/api/v1/periods/periods';
  static const String periodAttendanceEndpoint =
      '/api/v1/periods/attendance/period';
  static const String periodAttendanceStudentEndpoint =
      '/api/v1/periods/attendance/student';
  static const String healthEndpoint = '/api/v1/health';

  // Timeouts
  static const Duration connectTimeout = Duration(seconds: 10);
  static const Duration receiveTimeout = Duration(seconds: 30);

  // Get full URL
  static String getUrl(String endpoint) => '$baseUrl$endpoint';
}

/// Instructions for users:
///
/// 1. Find your laptop's IP address (see methods above)
/// 2. Make sure your phone and laptop are on the SAME WiFi network
/// 3. Update the baseUrl above with your laptop's IP
/// 4. Make sure the API server is running: uvicorn app.main:app --host 0.0.0.0 --port 8000
/// 5. Test connection by opening http://YOUR_LAPTOP_IP:8000/docs in your phone's browser
