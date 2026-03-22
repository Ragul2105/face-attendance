import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ThemeService extends ChangeNotifier {
  static const String _themeModeKey = 'theme_mode';

  final SharedPreferences _prefs;
  ThemeMode _themeMode = ThemeMode.system;

  ThemeService(this._prefs) {
    _loadThemeMode();
  }

  ThemeMode get themeMode => _themeMode;

  bool get isDarkMode {
    if (_themeMode == ThemeMode.dark) return true;
    if (_themeMode == ThemeMode.light) return false;
    return false;
  }

  void _loadThemeMode() {
    final savedMode = _prefs.getString(_themeModeKey);
    switch (savedMode) {
      case 'light':
        _themeMode = ThemeMode.light;
        break;
      case 'dark':
        _themeMode = ThemeMode.dark;
        break;
      default:
        _themeMode = ThemeMode.system;
    }
  }

  Future<void> toggleTheme() async {
    if (_themeMode == ThemeMode.dark) {
      _themeMode = ThemeMode.light;
      await _prefs.setString(_themeModeKey, 'light');
    } else {
      _themeMode = ThemeMode.dark;
      await _prefs.setString(_themeModeKey, 'dark');
    }
    notifyListeners();
  }
}
