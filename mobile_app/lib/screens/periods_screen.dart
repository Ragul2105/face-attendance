import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import 'camera_screen.dart';

class PeriodsScreen extends StatefulWidget {
  const PeriodsScreen({super.key});

  @override
  State<PeriodsScreen> createState() => _PeriodsScreenState();
}

class _PeriodsScreenState extends State<PeriodsScreen> {
  final TextEditingController _classController =
      TextEditingController(text: 'college');
  List<Period> _periods = [];
  Set<String> _markedPeriodIds = <String>{};
  bool _isLoading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadPeriods();
  }

  @override
  void dispose() {
    _classController.dispose();
    super.dispose();
  }

  int _todayWeekdayIndex() {
    final weekday = DateTime.now().weekday; // Mon=1...Sun=7
    return weekday - 1; // Mon=0...Sun=6
  }

  Future<void> _loadPeriods() async {
    if (!mounted) return;
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final auth = context.read<AuthService>();
      final api = context.read<ApiService>();
      final token = auth.accessToken;
      if (token == null) {
        throw Exception('Please login again');
      }

      final periods = await api.getClassPeriods(
        token: token,
        classId: _classController.text.trim(),
        dayOfWeek: _todayWeekdayIndex(),
      );

      final userId = auth.currentUser?.userId;
      final markedPeriodIds = <String>{};
      if (userId != null) {
        final history = await api.getPeriodAttendanceHistory(
          token: token,
          userId: userId,
        );
        final today = _todayDateIso();
        for (final record in history) {
          if (record.attendanceDate == today && record.status == 'present') {
            markedPeriodIds.add(record.periodId);
          }
        }
      }

      if (!mounted) return;
      setState(() {
        _periods = periods;
        _markedPeriodIds = markedPeriodIds;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
      });
    } finally {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
      });
    }
  }

  bool _isPeriodEnded(Period period) {
    final now = TimeOfDay.now();
    final endParts = period.endTime.split(':');
    if (endParts.length != 2) return false;
    final endHour = int.tryParse(endParts[0]) ?? 0;
    final endMinute = int.tryParse(endParts[1]) ?? 0;
    final nowTotal = now.hour * 60 + now.minute;
    final endTotal = endHour * 60 + endMinute;
    return nowTotal > endTotal;
  }

  bool _isPeriodStarted(Period period) {
    final now = TimeOfDay.now();
    final startParts = period.startTime.split(':');
    if (startParts.length != 2) return false;
    final startHour = int.tryParse(startParts[0]) ?? 0;
    final startMinute = int.tryParse(startParts[1]) ?? 0;
    final nowTotal = now.hour * 60 + now.minute;
    final startTotal = startHour * 60 + startMinute;
    return nowTotal >= startTotal;
  }

  bool _isPeriodActive(Period period) {
    return _isPeriodStarted(period) && !_isPeriodEnded(period);
  }

  String _todayDateIso() {
    final now = DateTime.now();
    final mm = now.month.toString().padLeft(2, '0');
    final dd = now.day.toString().padLeft(2, '0');
    return '${now.year}-$mm-$dd';
  }

  Future<void> _openCameraForPeriod(Period period) async {
    // Always open camera for the period - no time window restrictions
    final result = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => CameraScreen(periodForAttendance: period),
      ),
    );

    if (result == true && mounted) {
      await _loadPeriods();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Attendance marked for ${period.name}')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _loadPeriods,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Today\'s Periods',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _classController,
                    decoration: InputDecoration(
                      labelText: 'Class ID',
                      suffixIcon: IconButton(
                        icon: const Icon(Icons.search),
                        onPressed: _isLoading ? null : _loadPeriods,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 24),
              child: Center(child: CircularProgressIndicator()),
            )
          else if (_error != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 24),
              child: Text(
                _error!,
                textAlign: TextAlign.center,
              ),
            )
          else if (_periods.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 24),
              child: Text(
                'No periods found for today',
                textAlign: TextAlign.center,
              ),
            )
          else
            ..._periods.map(
              (period) {
                final isMarked = _markedPeriodIds.contains(period.periodId);
                final active = _isPeriodActive(period);
                return Card(
                  margin: const EdgeInsets.only(bottom: 10),
                  child: ListTile(
                    title: Text('${period.periodNumber}. ${period.name}'),
                    subtitle:
                        Text('${period.startTime} - ${period.endTime} (IST)'),
                    trailing: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: isMarked ? Colors.green : null,
                        foregroundColor: isMarked ? Colors.white : null,
                      ),
                      onPressed: isMarked
                          ? null
                          : (active
                              ? () => _openCameraForPeriod(period)
                              : null),
                      child: Text(
                          isMarked ? 'Marked' : (active ? 'Mark' : 'Closed')),
                    ),
                  ),
                );
              },
            ),
        ],
      ),
    );
  }
}
