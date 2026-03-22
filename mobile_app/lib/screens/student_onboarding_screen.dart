import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';

class StudentOnboardingScreen extends StatefulWidget {
  final StudentProgress student;

  const StudentOnboardingScreen({super.key, required this.student});

  @override
  State<StudentOnboardingScreen> createState() =>
      _StudentOnboardingScreenState();
}

class _StudentOnboardingScreenState extends State<StudentOnboardingScreen> {
  final ImagePicker _picker = ImagePicker();
  late int _uploadedCount;
  bool _isUploading = false;

  @override
  void initState() {
    super.initState();
    _uploadedCount = widget.student.uploadedImageCount;
  }

  Future<void> _pickAndUploadNext() async {
    if (_uploadedCount >= 10) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('All 10 images are already uploaded.')),
        );
      }
      return;
    }

    final slot = _uploadedCount + 1;

    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt),
              title: const Text('Take photo'),
              onTap: () => Navigator.pop(context, ImageSource.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library),
              title: const Text('Choose from gallery'),
              onTap: () => Navigator.pop(context, ImageSource.gallery),
            ),
          ],
        ),
      ),
    );

    if (source == null) return;

    final picked = await _picker.pickImage(
      source: source,
      imageQuality: 92,
    );

    if (picked == null) return;

    if (!mounted) return;
    final token = context.read<AuthService>().accessToken;
    if (token == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please login again')),
        );
      }
      return;
    }

    setState(() {
      _isUploading = true;
    });

    try {
      if (!mounted) return;
      final result = await context.read<ApiService>().uploadStudentImage(
            token: token,
            userId: widget.student.userId,
            imageIndex: slot,
            imageFile: File(picked.path),
          );

      final count =
          (result['uploadedImageCount'] as num?)?.toInt() ?? _uploadedCount;

      if (!mounted) return;
      setState(() {
        _uploadedCount = count;
      });

      final onboarded = result['isOnboarded'] == true;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            onboarded
                ? 'All 10 images uploaded. Student is now onboarded.'
                : 'Image uploaded for slot $slot ($_uploadedCount/10)',
          ),
        ),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString())),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isUploading = false;
        });
      }
    }
  }

  Future<void> _bulkUploadTenImages() async {
    if (!mounted) return;
    final token = context.read<AuthService>().accessToken;
    if (token == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please login again')),
        );
      }
      return;
    }

    final pickedList = await _picker.pickMultiImage(imageQuality: 92);
    if (pickedList.isEmpty) return;
    if (!mounted) return;

    if (pickedList.length != 10) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
                'Please select exactly 10 images (selected ${pickedList.length}).'),
          ),
        );
      }
      return;
    }

    final files = pickedList.map((x) => File(x.path)).toList();

    setState(() {
      _isUploading = true;
    });

    try {
      if (!mounted) return;
      final result = await context.read<ApiService>().uploadStudentImagesBulk(
            token: token,
            userId: widget.student.userId,
            imageFiles: files,
          );

      final count =
          (result['uploadedImageCount'] as num?)?.toInt() ?? _uploadedCount;
      if (!mounted) return;

      setState(() {
        _uploadedCount = count;
      });

      final onboarded = result['isOnboarded'] == true;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            onboarded
                ? 'Bulk upload complete. Student is now onboarded.'
                : 'Bulk upload completed ($_uploadedCount/10).',
          ),
        ),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString())),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isUploading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Student Onboarding'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.student.name,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 4),
                    Text('Student ID: ${widget.student.studentId}'),
                    const SizedBox(height: 12),
                    LinearProgressIndicator(value: _uploadedCount / 10),
                    const SizedBox(height: 8),
                    Text('Uploaded: $_uploadedCount / 10'),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _isUploading ? null : _pickAndUploadNext,
              icon: const Icon(Icons.add_a_photo),
              label: Text(
                _uploadedCount >= 10
                    ? 'All Images Uploaded'
                    : 'Upload Next Image (${_uploadedCount + 1}/10)',
              ),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: _isUploading ? null : _bulkUploadTenImages,
              icon: const Icon(Icons.collections),
              label: const Text('Bulk Upload 10 Images'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Note: Duplicate-face protection is enabled. Upload the actual student\'s face only.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            if (_isUploading)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: LinearProgressIndicator(),
              ),
          ],
        ),
      ),
    );
  }
}
