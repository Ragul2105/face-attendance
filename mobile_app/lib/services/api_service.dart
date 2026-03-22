import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'dart:convert';
import 'dart:typed_data';
import '../config/api_config.dart';
import '../models/models.dart';

class ApiService {
  Future<bool> checkHealth() async {
    try {
      final url = ApiConfig.getUrl(ApiConfig.healthEndpoint);
      final response = await http.get(Uri.parse(url)).timeout(
            ApiConfig.connectTimeout,
          );
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  Future<AttendanceResult> markAttendance({
    required File imageFile,
    required String token,
    String? sessionId,
  }) async {
    try {
      final url = ApiConfig.getUrl(ApiConfig.markAttendanceEndpoint);

      var request = http.MultipartRequest('POST', Uri.parse(url));

      // Add authorization header
      request.headers['Authorization'] = 'Bearer $token';

      // Add image file
      request.files.add(
        await http.MultipartFile.fromPath(
          'image',
          imageFile.path,
          contentType: MediaType('image', 'jpeg'),
        ),
      );

      // Add optional session ID
      if (sessionId != null) {
        request.fields['session_id'] = sessionId;
      }

      // Add camera_id
      request.fields['camera_id'] = 'mobile';

      // Send request
      final streamedResponse = await request.send().timeout(
            ApiConfig.receiveTimeout,
          );

      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return AttendanceResult.fromJson(json.decode(response.body));
      } else {
        throw Exception('Failed to mark attendance: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<AttendanceResult> markAttendanceWithPin({
    required String employeeId,
    required String pin,
    required String token,
  }) async {
    try {
      final url = ApiConfig.getUrl(ApiConfig.markAttendancePinEndpoint);

      var request = http.MultipartRequest('POST', Uri.parse(url));

      // Add authorization header
      request.headers['Authorization'] = 'Bearer $token';

      // Add fields
      request.fields['employee_id'] = employeeId;
      request.fields['pin'] = pin;
      request.fields['camera_id'] = 'mobile';

      // Send request
      final streamedResponse = await request.send().timeout(
            ApiConfig.receiveTimeout,
          );

      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return AttendanceResult.fromJson(json.decode(response.body));
      } else {
        throw Exception('Failed to mark attendance: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<List<AttendanceRecord>> getAttendanceHistory({
    required String userId,
    required String token,
    int limit = 30,
  }) async {
    try {
      final url = ApiConfig.getUrl(
          '${ApiConfig.attendanceHistoryEndpoint}/$userId?limit=$limit');

      final response = await http.get(
        Uri.parse(url),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      ).timeout(ApiConfig.receiveTimeout);

      if (response.statusCode == 200) {
        final List<dynamic> jsonList = json.decode(response.body);
        return jsonList.map((json) => AttendanceRecord.fromJson(json)).toList();
      } else {
        throw Exception('Failed to load attendance history');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<List<StudentProgress>> getStudentsProgress({
    required String token,
  }) async {
    try {
      final url = ApiConfig.getUrl(ApiConfig.studentsEndpoint);

      final response = await http.get(
        Uri.parse(url),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      ).timeout(ApiConfig.receiveTimeout);

      if (response.statusCode == 200) {
        final Map<String, dynamic> data = json.decode(response.body);
        final List<dynamic> students = data['students'] as List<dynamic>? ?? [];
        return students
            .map((json) =>
                StudentProgress.fromJson(json as Map<String, dynamic>))
            .toList();
      }

      throw Exception('Failed to load students progress: ${response.body}');
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<void> createStaff({
    required String name,
    required String staffId,
    required String pin,
    required String role,
    String? email,
    String department = 'college',
  }) async {
    try {
      final url = ApiConfig.getUrl(ApiConfig.staffEndpoint);

      final request = http.MultipartRequest('POST', Uri.parse(url));
      request.fields['name'] = name;
      request.fields['staff_id'] = staffId;
      request.fields['pin'] = pin;
      request.fields['role'] = role;
      request.fields['department'] = department;
      if (email != null && email.isNotEmpty) {
        request.fields['email'] = email;
      }

      final streamedResponse =
          await request.send().timeout(ApiConfig.receiveTimeout);
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode != 200) {
        throw Exception('Failed to create staff: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<void> createStudent({
    required String token,
    required String name,
    required String studentId,
    required String gender,
    required String email,
    required String pin,
    String department = 'college',
  }) async {
    try {
      final url = ApiConfig.getUrl(ApiConfig.studentsEndpoint);

      final request = http.MultipartRequest('POST', Uri.parse(url));
      request.headers['Authorization'] = 'Bearer $token';
      request.fields['name'] = name;
      request.fields['student_id'] = studentId;
      request.fields['gender'] = gender;
      request.fields['email'] = email;
      request.fields['pin'] = pin;
      request.fields['department'] = department;

      final streamedResponse =
          await request.send().timeout(ApiConfig.receiveTimeout);
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode != 200) {
        throw Exception('Failed to create student: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<void> bulkUploadStudentsCsv({
    required String token,
    required Uint8List csvBytes,
    required String filename,
    String? defaultPin,
  }) async {
    try {
      final url = ApiConfig.getUrl('${ApiConfig.studentsEndpoint}/bulk-upload');

      final request = http.MultipartRequest('POST', Uri.parse(url));
      request.headers['Authorization'] = 'Bearer $token';
      if (defaultPin != null && defaultPin.isNotEmpty) {
        request.fields['default_pin'] = defaultPin;
      }
      request.files.add(
        http.MultipartFile.fromBytes(
          'file',
          csvBytes,
          filename: filename,
          contentType: MediaType('text', 'csv'),
        ),
      );

      final streamedResponse =
          await request.send().timeout(ApiConfig.receiveTimeout);
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode != 200) {
        throw Exception('Failed to bulk upload students: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<Map<String, dynamic>> uploadStudentImage({
    required String token,
    required String userId,
    required int imageIndex,
    required File imageFile,
  }) async {
    try {
      final url =
          ApiConfig.getUrl('${ApiConfig.studentsEndpoint}/$userId/images');

      final request = http.MultipartRequest('POST', Uri.parse(url));
      request.headers['Authorization'] = 'Bearer $token';
      request.fields['image_index'] = imageIndex.toString();
      request.files.add(
        await http.MultipartFile.fromPath(
          'image',
          imageFile.path,
          contentType: MediaType('image', 'jpeg'),
        ),
      );

      final streamedResponse =
          await request.send().timeout(ApiConfig.receiveTimeout);
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }

      if (response.statusCode == 409) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        final detail = data['detail'];
        if (detail is Map<String, dynamic> &&
            detail['error'] == 'DUPLICATE_FACE') {
          throw Exception(
            'Duplicate face detected. These images match an existing registered user. '
            'Please upload the actual student\'s photos only.',
          );
        }
      }

      throw Exception('Failed to upload student image: ${response.body}');
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<Map<String, dynamic>> uploadStudentImagesBulk({
    required String token,
    required String userId,
    required List<File> imageFiles,
  }) async {
    try {
      final url =
          ApiConfig.getUrl('${ApiConfig.studentsEndpoint}/$userId/images/bulk');
      final request = http.MultipartRequest('POST', Uri.parse(url));
      request.headers['Authorization'] = 'Bearer $token';

      for (final file in imageFiles) {
        request.files.add(
          await http.MultipartFile.fromPath(
            'images',
            file.path,
            contentType: MediaType('image', 'jpeg'),
          ),
        );
      }

      final streamedResponse =
          await request.send().timeout(ApiConfig.receiveTimeout);
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }

      if (response.statusCode == 409) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        final detail = data['detail'];
        if (detail is Map<String, dynamic> &&
            detail['error'] == 'DUPLICATE_FACE') {
          throw Exception(
            'Duplicate face detected. Bulk images match an existing registered user. '
            'Please upload the correct student\'s photos.',
          );
        }
      }

      throw Exception('Failed to upload images in bulk: ${response.body}');
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<List<Period>> getClassPeriods({
    required String token,
    required String classId,
    int? dayOfWeek,
  }) async {
    try {
      final endpoint = dayOfWeek == null
          ? '${ApiConfig.periodsBaseEndpoint}/class/$classId'
          : '${ApiConfig.periodsBaseEndpoint}/class/$classId?day_of_week=$dayOfWeek';
      final url = ApiConfig.getUrl(endpoint);

      final response = await http.get(
        Uri.parse(url),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      ).timeout(ApiConfig.receiveTimeout);

      if (response.statusCode == 200) {
        final List<dynamic> jsonList = json.decode(response.body);
        return jsonList
            .map(
                (jsonItem) => Period.fromJson(jsonItem as Map<String, dynamic>))
            .toList();
      }

      throw Exception('Failed to load periods: ${response.body}');
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<PeriodAttendance> markPeriodAttendance({
    required String token,
    required String periodId,
    required String classId,
    required String attendanceDate,
    String status = 'present',
    double? studentLatitude,
    double? studentLongitude,
  }) async {
    try {
      final url = ApiConfig.getUrl(ApiConfig.periodAttendanceEndpoint);
      final request = http.MultipartRequest('POST', Uri.parse(url));
      request.headers['Authorization'] = 'Bearer $token';
      request.fields['periodId'] = periodId;
      request.fields['classId'] = classId;
      request.fields['attendanceDate'] = attendanceDate;
      request.fields['status'] = status;
      if (studentLatitude != null) {
        request.fields['studentLatitude'] = studentLatitude.toString();
      }
      if (studentLongitude != null) {
        request.fields['studentLongitude'] = studentLongitude.toString();
      }

      final streamedResponse =
          await request.send().timeout(ApiConfig.receiveTimeout);
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return PeriodAttendance.fromJson(
          json.decode(response.body) as Map<String, dynamic>,
        );
      }

      throw Exception('Failed to mark period attendance: ${response.body}');
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<Period> createPeriod({
    required String token,
    required int periodNumber,
    required String name,
    required String startTime,
    required String endTime,
    required int dayOfWeek,
    required String classId,
    double? campusLatitude,
    double? campusLongitude,
    double locationRadiusMeters = 200,
  }) async {
    try {
      final url = ApiConfig.getUrl(ApiConfig.periodsBaseEndpoint);
      final request = http.MultipartRequest('POST', Uri.parse(url));
      request.headers['Authorization'] = 'Bearer $token';
      request.fields['periodNumber'] = periodNumber.toString();
      request.fields['name'] = name;
      request.fields['startTime'] = startTime;
      request.fields['endTime'] = endTime;
      request.fields['dayOfWeek'] = dayOfWeek.toString();
      request.fields['classId'] = classId;
      if (campusLatitude != null) {
        request.fields['campusLatitude'] = campusLatitude.toString();
      }
      if (campusLongitude != null) {
        request.fields['campusLongitude'] = campusLongitude.toString();
      }
      request.fields['locationRadiusMeters'] = locationRadiusMeters.toString();

      final streamedResponse =
          await request.send().timeout(ApiConfig.receiveTimeout);
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return Period.fromJson(
            json.decode(response.body) as Map<String, dynamic>);
      }

      throw Exception('Failed to create period: ${response.body}');
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<List<PeriodAttendance>> getPeriodAttendanceHistory({
    required String token,
    required String userId,
  }) async {
    try {
      final url = ApiConfig.getUrl(
        '${ApiConfig.periodAttendanceStudentEndpoint}/$userId',
      );

      final response = await http.get(
        Uri.parse(url),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      ).timeout(ApiConfig.receiveTimeout);

      if (response.statusCode == 200) {
        final List<dynamic> jsonList = json.decode(response.body);
        return jsonList
            .map((jsonItem) =>
                PeriodAttendance.fromJson(jsonItem as Map<String, dynamic>))
            .toList();
      }

      throw Exception(
          'Failed to load period attendance history: ${response.body}');
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }
}
