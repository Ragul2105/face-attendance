import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../config/api_config.dart';
import '../models/models.dart';

class AuthService extends ChangeNotifier {
  final SharedPreferences _prefs;

  String? _accessToken;
  User? _currentUser;
  DateTime? _tokenExpiresAt;

  AuthService(this._prefs) {
    _loadFromStorage();
  }

  bool get isAuthenticated => _accessToken != null && !_isTokenExpired();
  User? get currentUser => _currentUser;
  String? get accessToken => _accessToken;

  bool _isTokenExpired() {
    if (_tokenExpiresAt == null) return true;
    return DateTime.now().isAfter(_tokenExpiresAt!);
  }

  void _loadFromStorage() {
    _accessToken = _prefs.getString('access_token');
    final userJson = _prefs.getString('user');
    final expiresStr = _prefs.getString('token_expires_at');

    if (userJson != null) {
      _currentUser = User.fromJson(json.decode(userJson));
    }

    if (expiresStr != null) {
      _tokenExpiresAt = DateTime.parse(expiresStr);
    }
  }

  Future<bool> login(
    String employeeId, {
    required String role,
    String? pin,
  }) async {
    try {
      final url = ApiConfig.getUrl(ApiConfig.loginEndpoint);

      final response = await http.post(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'employeeId': employeeId,
          'role': role,
          if (pin != null && pin.isNotEmpty) 'pin': pin,
        }),
      );

      if (response.statusCode == 200) {
        final loginResponse =
            LoginResponse.fromJson(json.decode(response.body));

        _accessToken = loginResponse.accessToken;
        _tokenExpiresAt = loginResponse.expiresAt;
        _currentUser = User(
          userId: loginResponse.userId,
          employeeId: loginResponse.employeeId,
          name: loginResponse.name,
          role: loginResponse.role,
        );

        // Save to storage
        await _prefs.setString('access_token', _accessToken!);
        await _prefs.setString('user', json.encode(_currentUser!.toJson()));
        await _prefs.setString(
            'token_expires_at', _tokenExpiresAt!.toIso8601String());

        notifyListeners();
        return true;
      } else if (response.statusCode == 404) {
        throw Exception('Employee ID not found');
      } else {
        throw Exception('Login failed: ${response.body}');
      }
    } catch (e) {
      debugPrint('Login error: $e');
      throw Exception('Login failed: $e');
    }
  }

  Future<void> logout() async {
    _accessToken = null;
    _currentUser = null;
    _tokenExpiresAt = null;

    await _prefs.remove('access_token');
    await _prefs.remove('user');
    await _prefs.remove('token_expires_at');

    notifyListeners();
  }

  Future<bool> verifyToken() async {
    if (!isAuthenticated) return false;

    try {
      final url = ApiConfig.getUrl(ApiConfig.verifyTokenEndpoint);

      final response = await http.post(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_accessToken',
        },
      );

      if (response.statusCode == 200) {
        return true;
      } else {
        await logout();
        return false;
      }
    } catch (e) {
      debugPrint('Token verification error: $e');
      return false;
    }
  }
}
