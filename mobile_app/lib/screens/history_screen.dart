import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../services/auth_service.dart';
import '../services/api_service.dart';
import '../models/models.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<AttendanceRecord> _records = [];
  List<PeriodAttendance> _periodRecords = [];
  bool _isLoading = false;
  String? _error;
  static const Duration _istOffset = Duration(hours: 5, minutes: 30);

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      if (!mounted) return;
      final authService = context.read<AuthService>();
      final apiService = context.read<ApiService>();

      if (authService.currentUser == null) return;

      final records = await apiService.getAttendanceHistory(
        userId: authService.currentUser!.userId,
        token: authService.accessToken!,
      );
      final periodRecords = await apiService.getPeriodAttendanceHistory(
        token: authService.accessToken!,
        userId: authService.currentUser!.userId,
      );
      if (!mounted) return;

      setState(() {
        _records = records;
        _periodRecords = periodRecords;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  String _formatDate(DateTime date) {
    final istDate = _toIst(date);
    final now = DateTime.now();
    final nowIst = _toIst(now);
    final diff = nowIst.difference(istDate);

    if (diff.inDays == 0) {
      return 'Today ${DateFormat.jm().format(istDate)} IST';
    } else if (diff.inDays == 1) {
      return 'Yesterday ${DateFormat.jm().format(istDate)} IST';
    } else {
      return '${DateFormat('MMM dd, yyyy - hh:mm a').format(istDate)} IST';
    }
  }

  DateTime _toIst(DateTime date) {
    return date.toUtc().add(_istOffset);
  }

  List<_HistoryItem> _buildItems() {
    final items = <_HistoryItem>[];

    for (final record in _records) {
      items.add(
        _HistoryItem(
          markedAt: record.markedAt,
          title: 'General Attendance',
          subtitle:
              'Session: ${record.sessionId} • Confidence: ${(record.confidence * 100).toStringAsFixed(1)}%',
          status: record.status,
          isPeriod: false,
        ),
      );
    }

    for (final record in _periodRecords) {
      final fallbackDate =
          DateTime.tryParse('${record.attendanceDate}T00:00:00') ??
              DateTime.now();
      items.add(
        _HistoryItem(
          markedAt: record.markedAt ?? fallbackDate,
          title: 'Period Attendance (${record.periodId})',
          subtitle: 'Class: ${record.classId} • Date: ${record.attendanceDate}',
          status: record.status,
          isPeriod: true,
        ),
      );
    }

    items.sort((a, b) => b.markedAt.compareTo(a.markedAt));
    return items;
  }

  @override
  Widget build(BuildContext context) {
    final items = _buildItems();

    return RefreshIndicator(
      onRefresh: _loadHistory,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Attendance History',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${items.length} records',
                          style:
                              Theme.of(context).textTheme.bodyMedium?.copyWith(
                                    color: Colors.grey[600],
                                  ),
                        ),
                      ],
                    ),
                    IconButton(
                      icon: const Icon(Icons.refresh),
                      onPressed: _isLoading ? null : _loadHistory,
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 16),

            // Content
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(
                                Icons.error_outline,
                                size: 64,
                                color: Colors.red,
                              ),
                              const SizedBox(height: 16),
                              Text(
                                'Error loading history',
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                              const SizedBox(height: 8),
                              Text(
                                _error!,
                                textAlign: TextAlign.center,
                                style: TextStyle(color: Colors.grey[600]),
                              ),
                              const SizedBox(height: 16),
                              ElevatedButton(
                                onPressed: _loadHistory,
                                child: const Text('Retry'),
                              ),
                            ],
                          ),
                        )
                      : items.isEmpty
                          ? Center(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(
                                    Icons.inbox_outlined,
                                    size: 64,
                                    color: Colors.grey[400],
                                  ),
                                  const SizedBox(height: 16),
                                  Text(
                                    'No attendance records yet',
                                    style: Theme.of(context)
                                        .textTheme
                                        .titleMedium
                                        ?.copyWith(
                                          color: Colors.grey[600],
                                        ),
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    'Mark your first attendance to see it here',
                                    style: TextStyle(color: Colors.grey[500]),
                                  ),
                                ],
                              ),
                            )
                          : ListView.builder(
                              itemCount: items.length,
                              itemBuilder: (context, index) {
                                final item = items[index];
                                return Card(
                                  margin: const EdgeInsets.only(bottom: 12),
                                  child: ListTile(
                                    leading: CircleAvatar(
                                      backgroundColor: item.isPeriod
                                          ? Colors.blue.shade100
                                          : Colors.green.shade100,
                                      child: Icon(
                                        item.isPeriod
                                            ? Icons.schedule
                                            : Icons.check,
                                        color: item.isPeriod
                                            ? Colors.blue.shade700
                                            : Colors.green.shade700,
                                      ),
                                    ),
                                    title: Text(
                                      _formatDate(item.markedAt),
                                      style: const TextStyle(
                                          fontWeight: FontWeight.bold),
                                    ),
                                    subtitle: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        const SizedBox(height: 4),
                                        Text(item.title),
                                        Text(item.subtitle),
                                      ],
                                    ),
                                    trailing: Chip(
                                      label: Text(item.status.toUpperCase()),
                                      backgroundColor: item.isPeriod
                                          ? Colors.blue.shade50
                                          : Colors.green.shade50,
                                    ),
                                  ),
                                );
                              },
                            ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HistoryItem {
  final DateTime markedAt;
  final String title;
  final String subtitle;
  final String status;
  final bool isPeriod;

  _HistoryItem({
    required this.markedAt,
    required this.title,
    required this.subtitle,
    required this.status,
    required this.isPeriod,
  });
}
