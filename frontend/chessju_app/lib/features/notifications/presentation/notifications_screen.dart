import 'package:chessju_app/core/errors/api_error.dart';
import 'package:chessju_app/core/network/content_repository.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class NotificationsScreen extends ConsumerStatefulWidget {
  const NotificationsScreen({super.key});

  @override
  ConsumerState<NotificationsScreen> createState() =>
      _NotificationsScreenState();
}

class _NotificationsScreenState extends ConsumerState<NotificationsScreen> {
  String? _message;
  bool _submitting = false;

  @override
  Widget build(BuildContext context) {
    final notifications = ref.watch(notificationsProvider);
    final unreadCount = ref.watch(unreadNotificationCountProvider);

    return AsyncValueView(
      value: notifications,
      onRetry: () => ref.invalidate(notificationsProvider),
      data: (data) => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'Notifications',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
              ),
              TextButton.icon(
                onPressed: _submitting ? null : _markAllRead,
                icon: const Icon(Icons.done_all),
                label: const Text('Read all'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          unreadCount.when(
            data: (count) => Text('$count unread'),
            loading: () => const Text('Loading unread count...'),
            error: (_, _) => const Text('Unread count unavailable'),
          ),
          if (_message != null) ...[const SizedBox(height: 8), Text(_message!)],
          const SizedBox(height: 16),
          if (data.items.isEmpty)
            const EmptyView('No notifications yet.')
          else
            for (final item in data.items)
              ContentCard(
                title: item.title,
                subtitle: item.body ?? item.type,
                leading: Icon(
                  item.readAt == null
                      ? Icons.notifications_active_outlined
                      : Icons.notifications_none,
                ),
                trailing: item.readAt == null
                    ? TextButton(
                        onPressed: _submitting
                            ? null
                            : () => _markOneRead(item.id),
                        child: const Text('Read'),
                      )
                    : const StatusChip('read'),
              ),
        ],
      ),
    );
  }

  Future<void> _markOneRead(String notificationId) async {
    await _submit(() async {
      await ref
          .read(contentRepositoryProvider)
          .markNotificationRead(notificationId);
      _message = 'Notification marked read.';
    });
  }

  Future<void> _markAllRead() async {
    await _submit(() async {
      await ref.read(contentRepositoryProvider).markAllNotificationsRead();
      _message = 'All notifications marked read.';
    });
  }

  Future<void> _submit(Future<void> Function() action) async {
    setState(() {
      _submitting = true;
      _message = null;
    });
    try {
      await action();
      ref.invalidate(notificationsProvider);
      ref.invalidate(unreadNotificationCountProvider);
    } on ApiException catch (exception) {
      _message = exception.error.message;
    } finally {
      if (mounted) {
        setState(() {
          _submitting = false;
        });
      }
    }
  }
}
