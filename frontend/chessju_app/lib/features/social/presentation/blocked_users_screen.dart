import 'package:chessju_app/core/errors/api_error.dart';
import 'package:chessju_app/features/social/data/social_repository.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class BlockedUsersScreen extends ConsumerStatefulWidget {
  const BlockedUsersScreen({super.key});

  @override
  ConsumerState<BlockedUsersScreen> createState() => _BlockedUsersScreenState();
}

class _BlockedUsersScreenState extends ConsumerState<BlockedUsersScreen> {
  bool _busy = false;
  String? _message;

  @override
  Widget build(BuildContext context) {
    final blocks = ref.watch(blocksProvider);

    return AsyncValueView(
      value: blocks,
      onRetry: () => ref.invalidate(blocksProvider),
      data: (data) => RefreshIndicator(
        onRefresh: () => ref.refresh(blocksProvider.future),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              'Blocked Users',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            const Text('Blocked users cannot send requests or messages.'),
            if (_message != null) ...[
              const SizedBox(height: 12),
              Text(_message!),
            ],
            const SizedBox(height: 16),
            if (data.items.isEmpty)
              const EmptyView('No blocked users.', icon: Icons.block)
            else
              for (final block in data.items)
                ContentCard(
                  title: block.blockedUser.displayName,
                  subtitle:
                      '@${block.blockedUser.username} | Blocked ${block.createdAt}',
                  leading: const Icon(Icons.block),
                  trailing: OutlinedButton(
                    onPressed: _busy
                        ? null
                        : () => _unblock(block.blockedUser.id),
                    child: const Text('Unblock'),
                  ),
                ),
          ],
        ),
      ),
    );
  }

  Future<void> _unblock(String userId) async {
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      await ref.read(socialRepositoryProvider).unblockUser(userId);
      ref.invalidate(blocksProvider);
      _message = 'User unblocked.';
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
