import 'package:chessju_app/core/errors/api_error.dart';
import 'package:chessju_app/core/network/content_repository.dart';
import 'package:chessju_app/features/auth/auth_controller.dart';
import 'package:chessju_app/features/auth/data/auth_models.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(profileProvider);

    return AsyncValueView(
      value: profile,
      onRetry: () => ref.invalidate(profileProvider),
      data: (user) => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Profile', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    user.profile.fullName,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text('@${user.profile.username}'),
                  Text(user.email),
                  if (user.profile.universityId != null)
                    Text('University ID: ${user.profile.universityId}'),
                  if (user.profile.chesscomUsername != null)
                    Text('Chess.com: ${user.profile.chesscomUsername}'),
                  const SizedBox(height: 16),
                  Text(
                    'Preferences',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  Text('App theme: ${user.preferences.appTheme}'),
                  Text('Board theme: ${user.preferences.boardTheme}'),
                  Text('Language: ${user.preferences.language}'),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 8,
                    children: [for (final role in user.roles) StatusChip(role)],
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 12,
                    runSpacing: 8,
                    children: [
                      OutlinedButton.icon(
                        onPressed: () => _showEditProfile(context, ref, user),
                        icon: const Icon(Icons.edit_outlined),
                        label: const Text('Edit profile'),
                      ),
                      FilledButton.icon(
                        onPressed: () async {
                          await ref
                              .read(authControllerProvider.notifier)
                              .logout();
                          if (context.mounted) {
                            context.go('/login');
                          }
                        },
                        icon: const Icon(Icons.logout),
                        label: const Text('Logout'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _showEditProfile(
    BuildContext context,
    WidgetRef ref,
    CurrentUser user,
  ) {
    return showDialog<void>(
      context: context,
      builder: (context) => _EditProfileDialog(user: user, ref: ref),
    );
  }
}

class _EditProfileDialog extends StatefulWidget {
  const _EditProfileDialog({required this.user, required this.ref});

  final CurrentUser user;
  final WidgetRef ref;

  @override
  State<_EditProfileDialog> createState() => _EditProfileDialogState();
}

class _EditProfileDialogState extends State<_EditProfileDialog> {
  late final TextEditingController _fullNameController;
  late final TextEditingController _universityIdController;
  late final TextEditingController _chesscomController;
  String? _error;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _fullNameController = TextEditingController(
      text: widget.user.profile.fullName,
    );
    _universityIdController = TextEditingController(
      text: widget.user.profile.universityId ?? '',
    );
    _chesscomController = TextEditingController(
      text: widget.user.profile.chesscomUsername ?? '',
    );
  }

  @override
  void dispose() {
    _fullNameController.dispose();
    _universityIdController.dispose();
    _chesscomController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Edit profile'),
      content: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _fullNameController,
              decoration: const InputDecoration(labelText: 'Full name'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _universityIdController,
              decoration: const InputDecoration(labelText: 'University ID'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _chesscomController,
              decoration: const InputDecoration(
                labelText: 'Chess.com username',
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _loading ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: _loading ? null : _save,
          child: _loading
              ? const SizedBox.square(
                  dimension: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Save'),
        ),
      ],
    );
  }

  Future<void> _save() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      await widget.ref
          .read(contentRepositoryProvider)
          .updateProfile(
            fullName: _fullNameController.text.trim(),
            universityId: _universityIdController.text.trim(),
            chesscomUsername: _chesscomController.text.trim(),
          );
      widget.ref.invalidate(profileProvider);
      if (mounted) {
        Navigator.of(context).pop();
      }
    } on ApiException catch (exception) {
      setState(() {
        _error = exception.error.message;
      });
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }
}
