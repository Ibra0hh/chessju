import 'package:chessju_app/core/errors/api_error.dart';
import 'package:chessju_app/features/social/data/social_models.dart';
import 'package:chessju_app/features/social/data/social_repository.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

class FriendsScreen extends ConsumerStatefulWidget {
  const FriendsScreen({super.key});

  @override
  ConsumerState<FriendsScreen> createState() => _FriendsScreenState();
}

class _FriendsScreenState extends ConsumerState<FriendsScreen> {
  bool _busy = false;
  String? _message;

  @override
  Widget build(BuildContext context) {
    final friends = ref.watch(friendsProvider);

    return AsyncValueView(
      value: friends,
      onRetry: () => ref.invalidate(friendsProvider),
      data: (data) => RefreshIndicator(
        onRefresh: () => ref.refresh(friendsProvider.future),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Friends',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                ),
                IconButton(
                  tooltip: 'Requests',
                  onPressed: () => context.go('/friend-requests'),
                  icon: const Icon(Icons.person_add_alt_1_outlined),
                ),
                IconButton(
                  tooltip: 'Conversations',
                  onPressed: () => context.go('/conversations'),
                  icon: const Icon(Icons.forum_outlined),
                ),
                IconButton(
                  tooltip: 'Blocked users',
                  onPressed: () => context.go('/blocks'),
                  icon: const Icon(Icons.block),
                ),
              ],
            ),
            const SizedBox(height: 8),
            const Text(
              'Open direct chats with friends or manage social safety.',
            ),
            if (_message != null) ...[
              const SizedBox(height: 12),
              Text(_message!),
            ],
            const SizedBox(height: 16),
            if (data.items.isEmpty)
              EmptyView(
                'No friends yet. Send or accept a friend request first.',
                icon: Icons.people_outline,
              )
            else
              for (final friend in data.items)
                ContentCard(
                  title: friend.displayName,
                  subtitle:
                      '@${friend.username} | Friends since ${friend.createdAt}',
                  leading: CircleAvatar(child: Text(_initial(friend))),
                  trailing: PopupMenuButton<String>(
                    onSelected: (value) => _handleFriendAction(value, friend),
                    itemBuilder: (context) => const [
                      PopupMenuItem(value: 'chat', child: Text('Open chat')),
                      PopupMenuItem(
                        value: 'remove',
                        child: Text('Remove friend'),
                      ),
                      PopupMenuItem(value: 'block', child: Text('Block user')),
                    ],
                  ),
                  onTap: () => _openConversation(friend),
                ),
          ],
        ),
      ),
    );
  }

  String _initial(SocialUser user) {
    final label = user.displayName.isNotEmpty
        ? user.displayName
        : user.username;
    return label.isEmpty ? '?' : label[0].toUpperCase();
  }

  Future<void> _handleFriendAction(String action, FriendUser friend) async {
    switch (action) {
      case 'chat':
        await _openConversation(friend);
        break;
      case 'remove':
        await _submit(() async {
          await ref.read(socialRepositoryProvider).removeFriend(friend.id);
          _message = 'Friend removed.';
        });
        break;
      case 'block':
        await _submit(() async {
          await ref.read(socialRepositoryProvider).blockUser(friend.id);
          _message = 'User blocked.';
        });
        break;
    }
  }

  Future<void> _openConversation(FriendUser friend) async {
    await _submit(() async {
      final conversation = await ref
          .read(socialRepositoryProvider)
          .createDirectConversation(friend.id);
      if (mounted) {
        context.go('/conversations/${conversation.id}');
      }
    }, refresh: false);
  }

  Future<void> _submit(
    Future<void> Function() action, {
    bool refresh = true,
  }) async {
    if (_busy) {
      return;
    }
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      await action();
      if (refresh) {
        ref.invalidate(friendsProvider);
        ref.invalidate(blocksProvider);
        ref.invalidate(conversationsProvider);
      }
    } on ApiException catch (exception) {
      _message = exception.error.message;
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }
}
