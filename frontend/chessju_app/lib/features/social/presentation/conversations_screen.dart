import 'package:chessju_app/features/auth/auth_controller.dart';
import 'package:chessju_app/features/social/data/social_models.dart';
import 'package:chessju_app/features/social/data/social_repository.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

class ConversationsScreen extends ConsumerWidget {
  const ConversationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final conversations = ref.watch(conversationsProvider);
    final currentUserId = ref.watch(authControllerProvider).user?.id;

    return AsyncValueView(
      value: conversations,
      onRetry: () => ref.invalidate(conversationsProvider),
      data: (data) => RefreshIndicator(
        onRefresh: () => ref.refresh(conversationsProvider.future),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Conversations',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                ),
                OutlinedButton.icon(
                  onPressed: () => context.go('/friends'),
                  icon: const Icon(Icons.people_outline),
                  label: const Text('Friends'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (data.items.isEmpty)
              const EmptyView(
                'No direct conversations yet. Open one from your friends list.',
                icon: Icons.forum_outlined,
              )
            else
              for (final conversation in data.items)
                _ConversationCard(
                  conversation: conversation,
                  currentUserId: currentUserId,
                  onTap: () => context.go('/conversations/${conversation.id}'),
                ),
          ],
        ),
      ),
    );
  }
}

class _ConversationCard extends StatelessWidget {
  const _ConversationCard({
    required this.conversation,
    required this.currentUserId,
    required this.onTap,
  });

  final Conversation conversation;
  final String? currentUserId;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final other = conversation.otherMember(currentUserId);
    final last = conversation.lastMessage;
    final subtitle = last == null
        ? 'No messages yet'
        : last.isDeleted
        ? 'Message deleted'
        : '${last.sender.username}: ${last.body ?? ''}';

    return ContentCard(
      title: other?.displayName ?? 'Direct conversation',
      subtitle: '$subtitle | ${conversation.updatedAt}',
      leading: const Icon(Icons.forum_outlined),
      trailing: const Icon(Icons.chevron_right),
      onTap: onTap,
    );
  }
}
