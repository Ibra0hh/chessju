import 'package:chessju_app/core/network/content_repository.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifications = ref.watch(notificationsProvider);
    final unreadCount = ref.watch(unreadNotificationCountProvider);

    return AsyncValueView(
      value: notifications,
      data: (data) => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Notifications',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 8),
          unreadCount.when(
            data: (count) => Text('$count unread'),
            loading: () => const Text('Loading unread count...'),
            error: (_, _) => const Text('Unread count unavailable'),
          ),
          const SizedBox(height: 16),
          if (data.items.isEmpty)
            const EmptyState('No notifications yet.')
          else
            for (final item in data.items)
              ContentCard(
                title: item.title,
                subtitle: item.body ?? item.type,
                trailing: item.readAt == null ? const Text('Unread') : null,
              ),
        ],
      ),
    );
  }
}
