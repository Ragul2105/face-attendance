class User {
  final String userId;
  final String employeeId;
  final String name;
  final String role;

  User({
    required this.userId,
    required this.employeeId,
    required this.name,
    required this.role,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      userId: json['userId'] as String,
      employeeId: json['employeeId'] as String,
      name: json['name'] as String,
      role: json['role'] as String? ?? 'employee',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'userId': userId,
      'employeeId': employeeId,
      'name': name,
      'role': role,
    };
  }
}

class LoginResponse {
  final String accessToken;
  final String userId;
  final String employeeId;
  final String name;
  final String role;
  final DateTime expiresAt;

  LoginResponse({
    required this.accessToken,
    required this.userId,
    required this.employeeId,
    required this.name,
    required this.role,
    required this.expiresAt,
  });

  factory LoginResponse.fromJson(Map<String, dynamic> json) {
    return LoginResponse(
      accessToken: json['accessToken'] as String,
      userId: json['userId'] as String,
      employeeId: json['employeeId'] as String,
      name: json['name'] as String,
      role: json['role'] as String,
      expiresAt: DateTime.parse(json['expiresAt'] as String),
    );
  }
}

class AttendanceRecord {
  final String recordId;
  final String userId;
  final String sessionId;
  final DateTime markedAt;
  final double confidence;
  final double livenessScore;
  final String cameraId;
  final String status;

  AttendanceRecord({
    required this.recordId,
    required this.userId,
    required this.sessionId,
    required this.markedAt,
    required this.confidence,
    required this.livenessScore,
    required this.cameraId,
    required this.status,
  });

  factory AttendanceRecord.fromJson(Map<String, dynamic> json) {
    return AttendanceRecord(
      recordId: json['recordId'] as String,
      userId: json['userId'] as String,
      sessionId: json['sessionId'] as String,
      markedAt: DateTime.parse(json['markedAt'] as String),
      confidence: (json['confidence'] as num).toDouble(),
      livenessScore: (json['livenessScore'] as num).toDouble(),
      cameraId: json['cameraId'] as String,
      status: json['status'] as String,
    );
  }
}

class AttendanceResult {
  final bool success;
  final String? userId;
  final String? userName;
  final String? employeeId;
  final double confidence;
  final String status;
  final String message;
  final DateTime? markedAt;

  AttendanceResult({
    required this.success,
    this.userId,
    this.userName,
    this.employeeId,
    required this.confidence,
    required this.status,
    required this.message,
    this.markedAt,
  });

  factory AttendanceResult.fromJson(Map<String, dynamic> json) {
    return AttendanceResult(
      success: json['success'] as bool,
      userId: json['userId'] as String?,
      userName: json['userName'] as String?,
      employeeId: json['employeeId'] as String?,
      confidence: (json['confidence'] as num).toDouble(),
      status: json['status'] as String,
      message: json['message'] as String,
      markedAt: json['markedAt'] != null
          ? DateTime.parse(json['markedAt'] as String)
          : null,
    );
  }
}

class StudentProgress {
  final String userId;
  final String studentId;
  final String name;
  final String? gender;
  final String? email;
  final bool isOnboarded;
  final int uploadedImageCount;
  final double attendancePercentage;
  final int attendedSessions;
  final int totalSessions;
  final bool isActive;

  StudentProgress({
    required this.userId,
    required this.studentId,
    required this.name,
    this.gender,
    this.email,
    required this.isOnboarded,
    required this.uploadedImageCount,
    required this.attendancePercentage,
    required this.attendedSessions,
    required this.totalSessions,
    required this.isActive,
  });

  factory StudentProgress.fromJson(Map<String, dynamic> json) {
    return StudentProgress(
      userId: json['userId'] as String,
      studentId: json['studentId'] as String,
      name: json['name'] as String,
      gender: json['gender'] as String?,
      email: json['email'] as String?,
      isOnboarded: json['isOnboarded'] as bool? ?? false,
      uploadedImageCount: json['uploadedImageCount'] as int? ?? 0,
      attendancePercentage:
          (json['attendancePercentage'] as num?)?.toDouble() ?? 0,
      attendedSessions: json['attendedSessions'] as int? ?? 0,
      totalSessions: json['totalSessions'] as int? ?? 0,
      isActive: json['isActive'] as bool? ?? true,
    );
  }
}

class Period {
  final String periodId;
  final String classId;
  final int periodNumber;
  final String name;
  final String startTime;
  final String endTime;
  final int dayOfWeek;
  final bool isActive;
  final double? campusLatitude;
  final double? campusLongitude;
  final double? locationRadiusMeters;

  Period({
    required this.periodId,
    required this.classId,
    required this.periodNumber,
    required this.name,
    required this.startTime,
    required this.endTime,
    required this.dayOfWeek,
    required this.isActive,
    this.campusLatitude,
    this.campusLongitude,
    this.locationRadiusMeters,
  });

  factory Period.fromJson(Map<String, dynamic> json) {
    return Period(
      periodId: json['periodId'] as String,
      classId: json['classId'] as String,
      periodNumber: json['periodNumber'] as int,
      name: json['name'] as String,
      startTime: json['startTime'] as String,
      endTime: json['endTime'] as String,
      dayOfWeek: json['dayOfWeek'] as int,
      isActive: json['isActive'] as bool? ?? true,
      campusLatitude: (json['campusLatitude'] as num?)?.toDouble(),
      campusLongitude: (json['campusLongitude'] as num?)?.toDouble(),
      locationRadiusMeters: (json['locationRadiusMeters'] as num?)?.toDouble(),
    );
  }
}

class PeriodAttendance {
  final String attendanceId;
  final String userId;
  final String periodId;
  final String classId;
  final String attendanceDate;
  final String status;
  final DateTime? markedAt;

  PeriodAttendance({
    required this.attendanceId,
    required this.userId,
    required this.periodId,
    required this.classId,
    required this.attendanceDate,
    required this.status,
    this.markedAt,
  });

  factory PeriodAttendance.fromJson(Map<String, dynamic> json) {
    return PeriodAttendance(
      attendanceId: json['attendanceId'] as String,
      userId: json['userId'] as String,
      periodId: json['periodId'] as String,
      classId: json['classId'] as String,
      attendanceDate: json['attendanceDate'] as String,
      status: json['status'] as String,
      markedAt: json['markedAt'] != null
          ? DateTime.tryParse(json['markedAt'] as String)
          : null,
    );
  }
}
