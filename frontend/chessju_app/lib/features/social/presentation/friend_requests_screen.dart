import 'package:chessju_app/core/errors/api_error.dart';
import 'package:chessju_app/features/social/data/social_models.dart';
import 'package:chessju_app/features/social/data/social_repository.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class FriendRequestsScreen extends ConsumerStatefulWidget {
  const FriendRequestsScreen({super.key});

  @override
  ConsumerState<FriendRequestsScreen> createState() =>
      _FriendRequestsScreenState();
}

class _FriendRequestsScreenState extends ConsumerState<FriendRequestsScreen> {
  final _receiverController = TextEditingController();
  bool _submitting = false;
  String? _message;

  @override
  void dispose() {
    _receiverController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final incoming = ref.watch(incomingFriendRequestsProvider);
    final outgoing = ref.watch(outgoingFriendRequestsProvider);

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(incomingFriendRequestsProvider);
        ref.invalidate(outgoingFriendRequestsProvider);
      },
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Friend Requests',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 8),
          const Text(
            'User search is not available yet. For local testing, send requests by user ID.',
          ),
          const SizedBox(height: 16),
          _SendRequestCard(
            controller: _receiverController,
            submitting: _submitting,
            onSubmit: _sendRequest,
          ),
          if (_message != null) ...[
            const SizedBox(height: 12),
            Text(_message!),
          ],
          const SizedBox(height: 24),
          Text('Incoming', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          AsyncValueView(
            value: incoming,
            onRetry: () => ref.invalidate(incomingFriendRequestsProvider),
            data: (data) => data.items.isEmpty
                ? const EmptyView('No incoming pending requests.')
                : Column(
                    children: [
                      for (final request in data.items)
                        _FriendRequestCard(
                          request: request,
                          currentSide: 'incoming',
                          onAccept: () => _accept(request),
                          onReject: () => _reject(request),
                        ),
                    ],
                  ),
          ),
          const SizedBox(height: 24),
          Text('Outgoing', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          AsyncValueView(
            value: outgoing,
            onRetry: () => ref.invalidate(outgoingFriendRequestsProvider),
            data: (data) => data.items.isEmpty
                ? const EmptyView('No outgoing pending requests.')
                : Column(
                    children: [
                      for (final request in data.items)
                        _FriendRequestCard(
                          request: request,
                          currentSide: 'outgoing',
                          onCancel: () => _cancel(request),
                        ),
                    ],
                  ),
          ),
        ],
      ),
    );
  }

  Future<void> _sendRequest() async {
    final receiverId = _receiverController.text.trim();
    if (receiverId.isEmpty) {
      setState(() {
        _message = 'Enter a receiver user ID.';
      });
      return;
    }
    await _submit(() async {
      await ref.read(socialRepositoryProvider).sendFriendRequest(receiverId);
      _receiverController.clear();
      _message = 'Friend request sent.';
    });
  }

  Future<void> _accept(FriendRequest request) async {
    await _submit(() async {
      await ref.read(socialRepositoryProvider).acceptFriendRequest(request.id);
      _message = 'Friend request accepted.';
    });
  }

  Future<void> _reject(FriendRequest request) async {
    await _submit(() async {
      await ref.read(socialRepositoryProvider).rejectFriendRequest(request.id);
      _message = 'Friend request rejected.';
    });
  }

  Future<void> _cancel(FriendRequest request) async {
    await _submit(() async {
      await ref.read(socialRepositoryProvider).cancelFriendRequest(request.id);
      _message = 'Friend request cancelled.';
    });
  }

  Future<void> _submit(Future<void> Function() action) async {
    setState(() {
      _submitting = true;
      _message = null;
    });
    try {
      await action();
      ref.invalidate(incomingFriendRequestsProvider);
      ref.invalidate(outgoingFriendRequestsProvider);
      ref.invalidate(friendsProvider);
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

class _SendRequestCard extends StatelessWidget {
  const _SendRequestCard({
    required this.controller,
    required this.submitting,
    required this.onSubmit,
  });

  final TextEditingController controller;
  final bool submitting;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Send request', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                labelText: 'Receiver user ID',
                prefixIcon: Icon(Icons.tag_outlined),
              ),
            ),
            const SizedBox(height: 12),
            PrimaryButton(
              label: 'Send request',
              icon: Icons.person_add_alt_1_outlined,
              loading: submitting,
              onPressed: onSubmit,
            ),
          ],
        ),
      ),
    );
  }
}

class _FriendRequestCard extends StatelessWidget {
  const _FriendRequestCard({
    required this.request,
    required this.currentSide,
    this.onAccept,
    this.onReject,
    this.onCancel,
  });

  final FriendRequest request;
  final String currentSide;
  final VoidCallback? onAccept;
  final VoidCallback? onReject;
  final VoidCallback? onCancel;

  @override
  Widget build(BuildContext context) {
    final other = currentSide == 'incoming' ? request.sender : request.receiver;
    return ContentCard(
      title: other.displayName,
      subtitle: '@${other.username} | ${request.createdAt}',
      leading: const Icon(Icons.person_outline),
      trailing: Wrap(
        spacing: 8,
        children: [
          StatusChip(request.status),
          if (onAccept != null)
            IconButton(
              tooltip: 'Accept',
              onPressed: onAccept,
              icon: const Icon(Icons.check_circle_outline),
            ),
          if (onReject != null)
            IconButton(
              tooltip: 'Reject',
              onPressed: onReject,
              icon: const Icon(Icons.close),
            ),
          if (onCancel != null)
            IconButton(
              tooltip: 'Cancel',
              onPressed: onCancel,
              icon: const Icon(Icons.cancel_outlined),
            ),
        ],
      ),
    );
  }
}
