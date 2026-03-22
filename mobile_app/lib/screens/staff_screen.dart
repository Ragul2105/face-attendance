import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';
import 'package:geolocator/geolocator.dart';
import '../services/auth_service.dart';
import '../services/api_service.dart';
import '../models/models.dart';
import 'student_onboarding_screen.dart';

class StaffScreen extends StatefulWidget {
  const StaffScreen({super.key});

  @override
  State<StaffScreen> createState() => _StaffScreenState();
}

class _StaffScreenState extends State<StaffScreen> {
  List<StudentProgress> _students = [];
  bool _isLoading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadStudents();
  }

  Future<void> _loadStudents() async {
    if (!mounted) return;

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      if (!mounted) return;
      final authService = context.read<AuthService>();
      final apiService = context.read<ApiService>();

      if (authService.accessToken == null) {
        throw Exception('No access token');
      }

      final students = await apiService.getStudentsProgress(
        token: authService.accessToken!,
      );

      if (!mounted) return;
      setState(() {
        _students = students;
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

  Future<void> _showAddStudentDialog() async {
    final formKey = GlobalKey<FormState>();
    final nameController = TextEditingController();
    final studentIdController = TextEditingController();
    final pinController = TextEditingController();
    final emailController = TextEditingController();
    String selectedGender = 'male';
    final parentContext = context;
    final token = parentContext.read<AuthService>().accessToken;
    final apiService = parentContext.read<ApiService>();

    final dialogResult = await showDialog<Map<String, String>>(
      context: parentContext,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (dialogContext, setDialogState) {
            return AlertDialog(
              title: const Text('Add Student'),
              content: Form(
                key: formKey,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      TextFormField(
                        controller: nameController,
                        decoration: const InputDecoration(labelText: 'Name'),
                        validator: (v) => (v == null || v.trim().isEmpty)
                            ? 'Enter name'
                            : null,
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: studentIdController,
                        decoration:
                            const InputDecoration(labelText: 'Student ID'),
                        validator: (v) => (v == null || v.trim().isEmpty)
                            ? 'Enter student ID'
                            : null,
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: pinController,
                        obscureText: true,
                        decoration: const InputDecoration(labelText: 'PIN'),
                        validator: (v) => (v == null || v.trim().isEmpty)
                            ? 'Enter PIN'
                            : null,
                      ),
                      const SizedBox(height: 8),
                      DropdownButtonFormField<String>(
                        value: selectedGender,
                        decoration: const InputDecoration(labelText: 'Gender'),
                        items: const [
                          DropdownMenuItem(value: 'male', child: Text('Male')),
                          DropdownMenuItem(
                              value: 'female', child: Text('Female')),
                          DropdownMenuItem(
                              value: 'other', child: Text('Other')),
                        ],
                        onChanged: (value) {
                          if (value == null) return;
                          setDialogState(() {
                            selectedGender = value;
                          });
                        },
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: emailController,
                        decoration: const InputDecoration(labelText: 'Email'),
                        validator: (v) => (v == null || v.trim().isEmpty)
                            ? 'Enter email'
                            : null,
                      ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(dialogContext).pop(),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () {
                    if (!formKey.currentState!.validate()) return;
                    Navigator.of(dialogContext).pop({
                      'name': nameController.text.trim(),
                      'studentId': studentIdController.text.trim(),
                      'gender': selectedGender,
                      'email': emailController.text.trim(),
                      'pin': pinController.text.trim(),
                    });
                  },
                  child: const Text('Create'),
                ),
              ],
            );
          },
        );
      },
    );

    if (dialogResult == null) {
      nameController.dispose();
      studentIdController.dispose();
      pinController.dispose();
      emailController.dispose();
      return;
    }

    if (token == null) {
      if (mounted) {
        ScaffoldMessenger.of(parentContext).showSnackBar(
          const SnackBar(content: Text('Please login again')),
        );
      }
      nameController.dispose();
      studentIdController.dispose();
      pinController.dispose();
      emailController.dispose();
      return;
    }

    try {
      await apiService.createStudent(
        token: token,
        name: dialogResult['name']!,
        studentId: dialogResult['studentId']!,
        gender: dialogResult['gender']!,
        email: dialogResult['email']!,
        pin: dialogResult['pin']!,
      );

      if (mounted) {
        ScaffoldMessenger.of(parentContext).showSnackBar(
          const SnackBar(content: Text('Student created successfully')),
        );
      }
      await _loadStudents();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(parentContext).showSnackBar(
          SnackBar(content: Text(e.toString())),
        );
      }
    }

    nameController.dispose();
    studentIdController.dispose();
    pinController.dispose();
    emailController.dispose();
  }

  Future<void> _bulkUploadCsv() async {
    if (!mounted) return;

    final authService = context.read<AuthService>();
    final apiService = context.read<ApiService>();
    final token = authService.accessToken;

    if (token == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please login again')),
        );
      }
      return;
    }

    final file = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['csv'],
      withData: true,
    );

    if (file == null || file.files.isEmpty) {
      return;
    }

    final picked = file.files.first;
    if (picked.bytes == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Unable to read selected CSV file')),
        );
      }
      return;
    }

    try {
      await apiService.bulkUploadStudentsCsv(
        token: token,
        csvBytes: picked.bytes!,
        filename: picked.name,
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('CSV uploaded successfully')),
        );
        _loadStudents();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString())),
        );
      }
    }
  }

  Future<void> _showCreatePeriodDialog() async {
    final formKey = GlobalKey<FormState>();
    final periodNumberController = TextEditingController();
    final nameController = TextEditingController();
    final startTimeController = TextEditingController();
    final endTimeController = TextEditingController();
    final classIdController = TextEditingController(text: 'college');
    final locationRadiusController = TextEditingController(text: '200');
    double? campusLatitude;
    double? campusLongitude;
    int selectedDay = DateTime.now().weekday - 1;
    final parentContext = context;

    final data = await showDialog<Map<String, dynamic>>(
      context: parentContext,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (dialogContext, setDialogState) {
            return AlertDialog(
              title: const Text('Create Period'),
              content: Form(
                key: formKey,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      TextFormField(
                        controller: periodNumberController,
                        keyboardType: TextInputType.number,
                        decoration:
                            const InputDecoration(labelText: 'Period Number'),
                        validator: (v) => (v == null || v.trim().isEmpty)
                            ? 'Enter period number'
                            : null,
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: nameController,
                        decoration:
                            const InputDecoration(labelText: 'Period Name'),
                        validator: (v) => (v == null || v.trim().isEmpty)
                            ? 'Enter period name'
                            : null,
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: startTimeController,
                        decoration: const InputDecoration(
                            labelText: 'Start Time (HH:MM)'),
                        validator: (v) => (v == null || v.trim().isEmpty)
                            ? 'Enter start time'
                            : null,
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: endTimeController,
                        decoration: const InputDecoration(
                            labelText: 'End Time (HH:MM)'),
                        validator: (v) => (v == null || v.trim().isEmpty)
                            ? 'Enter end time'
                            : null,
                      ),
                      const SizedBox(height: 8),
                      DropdownButtonFormField<int>(
                        value: selectedDay,
                        decoration:
                            const InputDecoration(labelText: 'Day of Week'),
                        items: const [
                          DropdownMenuItem(value: 0, child: Text('Monday')),
                          DropdownMenuItem(value: 1, child: Text('Tuesday')),
                          DropdownMenuItem(value: 2, child: Text('Wednesday')),
                          DropdownMenuItem(value: 3, child: Text('Thursday')),
                          DropdownMenuItem(value: 4, child: Text('Friday')),
                          DropdownMenuItem(value: 5, child: Text('Saturday')),
                          DropdownMenuItem(value: 6, child: Text('Sunday')),
                        ],
                        onChanged: (v) {
                          if (v == null) return;
                          setDialogState(() {
                            selectedDay = v;
                          });
                        },
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: classIdController,
                        decoration:
                            const InputDecoration(labelText: 'Class ID'),
                        validator: (v) => (v == null || v.trim().isEmpty)
                            ? 'Enter class ID'
                            : null,
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: locationRadiusController,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(
                          labelText: 'Allowed Radius (meters)',
                        ),
                        validator: (v) => (v == null || v.trim().isEmpty)
                            ? 'Enter radius'
                            : null,
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              campusLatitude == null || campusLongitude == null
                                  ? 'Campus location: not set'
                                  : 'Campus location: ${campusLatitude!.toStringAsFixed(6)}, ${campusLongitude!.toStringAsFixed(6)}',
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ),
                          TextButton.icon(
                            onPressed: () async {
                              try {
                                final serviceEnabled =
                                    await Geolocator.isLocationServiceEnabled();
                                if (!serviceEnabled) {
                                  throw Exception('Enable location services');
                                }

                                LocationPermission permission =
                                    await Geolocator.checkPermission();
                                if (permission == LocationPermission.denied) {
                                  permission =
                                      await Geolocator.requestPermission();
                                }
                                if (permission == LocationPermission.denied ||
                                    permission ==
                                        LocationPermission.deniedForever) {
                                  throw Exception('Location permission denied');
                                }

                                final position =
                                    await Geolocator.getCurrentPosition(
                                  desiredAccuracy: LocationAccuracy.high,
                                );

                                setDialogState(() {
                                  campusLatitude = position.latitude;
                                  campusLongitude = position.longitude;
                                });
                              } catch (e) {
                                if (mounted) {
                                  ScaffoldMessenger.of(parentContext)
                                      .showSnackBar(
                                    SnackBar(
                                        content: Text('Location error: $e')),
                                  );
                                }
                              }
                            },
                            icon: const Icon(Icons.my_location),
                            label: const Text('Use Current'),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(dialogContext).pop(),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () {
                    if (!formKey.currentState!.validate()) return;
                    Navigator.of(dialogContext).pop({
                      'periodNumber':
                          int.parse(periodNumberController.text.trim()),
                      'name': nameController.text.trim(),
                      'startTime': startTimeController.text.trim(),
                      'endTime': endTimeController.text.trim(),
                      'dayOfWeek': selectedDay,
                      'classId': classIdController.text.trim(),
                      'locationRadiusMeters':
                          double.parse(locationRadiusController.text.trim()),
                      'campusLatitude': campusLatitude,
                      'campusLongitude': campusLongitude,
                    });
                  },
                  child: const Text('Create'),
                ),
              ],
            );
          },
        );
      },
    );

    if (data == null) {
      periodNumberController.dispose();
      nameController.dispose();
      startTimeController.dispose();
      endTimeController.dispose();
      classIdController.dispose();
      locationRadiusController.dispose();
      return;
    }

    try {
      final token = parentContext.read<AuthService>().accessToken;
      if (token == null) {
        throw Exception('Please login again');
      }

      await parentContext.read<ApiService>().createPeriod(
            token: token,
            periodNumber: data['periodNumber'] as int,
            name: data['name'] as String,
            startTime: data['startTime'] as String,
            endTime: data['endTime'] as String,
            dayOfWeek: data['dayOfWeek'] as int,
            classId: data['classId'] as String,
            locationRadiusMeters: data['locationRadiusMeters'] as double,
            campusLatitude: data['campusLatitude'] as double?,
            campusLongitude: data['campusLongitude'] as double?,
          );

      if (mounted) {
        ScaffoldMessenger.of(parentContext).showSnackBar(
          const SnackBar(content: Text('Period created successfully')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(parentContext).showSnackBar(
          SnackBar(content: Text(e.toString())),
        );
      }
    }

    periodNumberController.dispose();
    nameController.dispose();
    startTimeController.dispose();
    endTimeController.dispose();
    classIdController.dispose();
    locationRadiusController.dispose();
  }

  Color _attendanceColor(double percentage) {
    if (percentage >= 75) return Colors.green;
    if (percentage >= 50) return Colors.orange;
    return Colors.red;
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _loadStudents,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Students',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${_students.length} students',
                          style: Theme.of(context)
                              .textTheme
                              .bodyMedium
                              ?.copyWith(color: Colors.grey[600]),
                        ),
                      ],
                    ),
                    Row(
                      children: [
                        IconButton(
                          icon: const Icon(Icons.person_add_alt_1),
                          tooltip: 'Add Student',
                          onPressed: _showAddStudentDialog,
                        ),
                        IconButton(
                          icon: const Icon(Icons.upload_file),
                          tooltip: 'Bulk Upload CSV',
                          onPressed: _bulkUploadCsv,
                        ),
                        IconButton(
                          icon: const Icon(Icons.schedule),
                          tooltip: 'Create Period',
                          onPressed: _showCreatePeriodDialog,
                        ),
                        IconButton(
                          icon: const Icon(Icons.refresh),
                          onPressed: _isLoading ? null : _loadStudents,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(
                          child: Text(
                            _error!,
                            textAlign: TextAlign.center,
                          ),
                        )
                      : _students.isEmpty
                          ? const Center(
                              child: Text('No students found'),
                            )
                          : ListView.builder(
                              itemCount: _students.length,
                              itemBuilder: (context, index) {
                                final student = _students[index];
                                final color = _attendanceColor(
                                    student.attendancePercentage);

                                return Card(
                                  margin: const EdgeInsets.only(bottom: 12),
                                  child: ListTile(
                                    title: Text(
                                        '${student.name} (${student.studentId})'),
                                    onTap: () async {
                                      await Navigator.of(context).push(
                                        MaterialPageRoute(
                                          builder: (_) =>
                                              StudentOnboardingScreen(
                                            student: student,
                                          ),
                                        ),
                                      );

                                      if (mounted) {
                                        _loadStudents();
                                      }
                                    },
                                    subtitle: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        const SizedBox(height: 6),
                                        Text(
                                          'Onboarding: ${student.uploadedImageCount}/10 images',
                                        ),
                                        Text(
                                          'Attendance: ${student.attendancePercentage.toStringAsFixed(1)}% '
                                          '(${student.attendedSessions}/${student.totalSessions})',
                                          style: TextStyle(color: color),
                                        ),
                                      ],
                                    ),
                                    trailing: Chip(
                                      label: Text(
                                        student.isOnboarded
                                            ? 'READY'
                                            : 'PENDING',
                                      ),
                                      backgroundColor: student.isOnboarded
                                          ? Colors.green.shade50
                                          : Colors.orange.shade50,
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
