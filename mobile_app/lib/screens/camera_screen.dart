import 'dart:io';
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../services/api_service.dart';
import '../models/models.dart';

class CameraScreen extends StatefulWidget {
  final Period? periodForAttendance;

  const CameraScreen({super.key, this.periodForAttendance});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  final ImagePicker _picker = ImagePicker();
  File? _imageFile;
  bool _isProcessing = false;
  bool _periodMarkSaved = false;

  String _todayDateIso() {
    final now = DateTime.now();
    final mm = now.month.toString().padLeft(2, '0');
    final dd = now.day.toString().padLeft(2, '0');
    return '${now.year}-$mm-$dd';
  }

  Future<Position> _getCurrentLocation() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      throw Exception('Location services are disabled. Please enable GPS.');
    }

    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      throw Exception('Location permission is required for period attendance');
    }

    return Geolocator.getCurrentPosition(
      desiredAccuracy: LocationAccuracy.high,
    );
  }

  Future<void> _markCurrentPeriodAttendance() async {
    final period = widget.periodForAttendance;
    if (period == null) {
      return;
    }

    final authService = context.read<AuthService>();
    final apiService = context.read<ApiService>();
    final position = await _getCurrentLocation();

    // Allow marking at any time (no period window restriction)
    await apiService.markPeriodAttendance(
      token: authService.accessToken!,
      periodId: period.periodId,
      classId: period.classId,
      attendanceDate: _todayDateIso(),
      studentLatitude: position.latitude,
      studentLongitude: position.longitude,
    );
  }

  Future<void> _captureImage(ImageSource source) async {
    try {
      final XFile? photo = await _picker.pickImage(
        source: source,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 85,
      );

      if (photo != null) {
        setState(() {
          _imageFile = File(photo.path);
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error capturing image: $e')),
        );
      }
    }
  }

  Future<void> _markAttendance() async {
    if (_imageFile == null) return;

    _periodMarkSaved = widget.periodForAttendance == null;
    setState(() => _isProcessing = true);

    try {
      final authService = context.read<AuthService>();
      final apiService = context.read<ApiService>();

      final result = await apiService.markAttendance(
        imageFile: _imageFile!,
        token: authService.accessToken!,
      );

      AttendanceResult finalResult = result;

      // If face recognition succeeds AND period is provided, mark period attendance
      if (result.success && widget.periodForAttendance != null) {
        try {
          await _markCurrentPeriodAttendance();
          _periodMarkSaved = true;
        } catch (e) {
          _periodMarkSaved = false;
          finalResult = AttendanceResult(
            success: false,
            userId: result.userId,
            userName: result.userName,
            employeeId: result.employeeId,
            confidence: result.confidence,
            status: 'failed',
            message: 'Face matched, but period attendance was not saved: $e',
            markedAt: result.markedAt,
          );
        }
      }

      if (mounted) {
        _showResultDialog(finalResult);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      setState(() => _isProcessing = false);
    }
  }

  void _showResultDialog(AttendanceResult result) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        icon: Icon(
          result.success ? Icons.check_circle : Icons.error,
          color: result.success ? Colors.green : Colors.red,
          size: 64,
        ),
        title: Text(result.success ? 'Success!' : 'Failed'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (result.userName != null)
              Text(
                result.userName!,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
            const SizedBox(height: 8),
            Text(result.message),
            if (result.confidence > 0) ...[
              const SizedBox(height: 16),
              Text(
                'Confidence: ${(result.confidence * 100).toStringAsFixed(1)}%',
                style: TextStyle(color: Colors.grey[600]),
              ),
            ],
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              if (result.success) {
                setState(() => _imageFile = null);
                if (widget.periodForAttendance != null && _periodMarkSaved) {
                  Navigator.of(this.context).pop(true);
                }
              }
            },
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  void _clearImage() {
    setState(() {
      _imageFile = null;
    });
  }

  void _showPinDialog() {
    // Extract services from parent context BEFORE showing dialog
    final parentContext = context;
    final authService = parentContext.read<AuthService>();
    final apiService = parentContext.read<ApiService>();
    final user = authService.currentUser;

    if (user == null) {
      ScaffoldMessenger.of(parentContext).showSnackBar(
        const SnackBar(content: Text('User not logged in')),
      );
      return;
    }

    final pinController = TextEditingController();
    bool _isPinProcessing = false;

    showDialog(
      context: parentContext,
      barrierDismissible: false,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('Mark Attendance with PIN'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Face detection failed. Please enter your PIN to mark attendance.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
              TextField(
                controller: pinController,
                obscureText: true,
                keyboardType: TextInputType.number,
                maxLength: 4,
                decoration: InputDecoration(
                  labelText: 'PIN',
                  hintText: 'Enter your 4-digit PIN',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: _isPinProcessing
                  ? null
                  : () async {
                      final pin = pinController.text.trim();
                      if (pin.isEmpty) {
                        if (mounted) {
                          ScaffoldMessenger.of(parentContext).showSnackBar(
                            const SnackBar(
                                content: Text('Please enter your PIN')),
                          );
                        }
                        return;
                      }

                      setState(() => _isPinProcessing = true);

                      try {
                        _periodMarkSaved = widget.periodForAttendance == null;
                        final result = await apiService.markAttendanceWithPin(
                          employeeId: user.employeeId,
                          pin: pin,
                          token: authService.accessToken!,
                        );

                        AttendanceResult finalResult = result;

                        if (result.success &&
                            widget.periodForAttendance != null) {
                          try {
                            await _markCurrentPeriodAttendance();
                            _periodMarkSaved = true;
                          } catch (e) {
                            _periodMarkSaved = false;
                            finalResult = AttendanceResult(
                              success: false,
                              userId: result.userId,
                              userName: result.userName,
                              employeeId: result.employeeId,
                              confidence: result.confidence,
                              status: 'failed',
                              message:
                                  'PIN verified, but period attendance was not saved: $e',
                              markedAt: result.markedAt,
                            );
                          }
                        }

                        if (mounted) {
                          Navigator.of(dialogContext).pop();
                          _showResultDialog(finalResult);
                        }
                      } catch (e) {
                        if (mounted) {
                          ScaffoldMessenger.of(parentContext).showSnackBar(
                            SnackBar(
                              content: Text('Error: $e'),
                              backgroundColor: Colors.red,
                            ),
                          );
                        }
                      } finally {
                        setState(() => _isPinProcessing = false);
                      }
                    },
              child: _isPinProcessing
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Submit'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthService>().currentUser;
    final period = widget.periodForAttendance;

    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Welcome Card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Welcome, ${user?.name ?? "User"}!',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  if (period != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      'Period: ${period.periodNumber}. ${period.name} (${period.startTime}-${period.endTime} IST)',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                  const SizedBox(height: 8),
                  Text(
                    'Employee ID: ${user?.employeeId ?? "N/A"}',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Colors.grey[600],
                        ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 24),

          // Instructions
          Text(
            period == null
                ? 'Capture your photo to mark attendance'
                : 'Capture your photo (or use PIN) to mark attendance for this period',
            style: Theme.of(context).textTheme.titleMedium,
            textAlign: TextAlign.center,
          ),

          const SizedBox(height: 16),

          // Image Preview
          Expanded(
            child: _imageFile != null
                ? Container(
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.grey),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Image.file(
                        _imageFile!,
                        fit: BoxFit.contain,
                      ),
                    ),
                  )
                : Container(
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.grey, width: 2),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.camera_alt_outlined,
                          size: 80,
                          color: Colors.grey[400],
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'No image captured',
                          style: TextStyle(
                            color: Colors.grey[600],
                            fontSize: 16,
                          ),
                        ),
                      ],
                    ),
                  ),
          ),

          const SizedBox(height: 24),

          // Action Buttons
          if (_imageFile == null) ...[
            ElevatedButton.icon(
              onPressed: () => _captureImage(ImageSource.camera),
              icon: const Icon(Icons.camera_alt),
              label: const Text('Take Photo'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () => _captureImage(ImageSource.gallery),
              icon: const Icon(Icons.photo_library),
              label: const Text('Choose from Gallery'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),
            const SizedBox(height: 16),
            Divider(color: Colors.grey[300]),
            const SizedBox(height: 16),
            Text(
              'Face detection not working? Use PIN instead',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.grey[600],
                fontSize: 12,
              ),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: _showPinDialog,
              icon: const Icon(Icons.lock),
              label: const Text('Mark Attendance with PIN'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                side: BorderSide(color: Colors.orange[700]!),
              ),
            ),
          ] else ...[
            ElevatedButton.icon(
              onPressed: _isProcessing ? null : _markAttendance,
              icon: _isProcessing
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.check),
              label: Text(_isProcessing ? 'Processing...' : 'Mark Attendance'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: _isProcessing ? null : _clearImage,
              icon: const Icon(Icons.refresh),
              label: const Text('Retake Photo'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
