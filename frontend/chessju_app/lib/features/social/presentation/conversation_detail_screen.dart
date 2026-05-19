import 'package:chessju_app/core/errors/api_error.dart';
import 'package:chessju_app/features/auth/auth_controller.dart';
import 'package:chessju_app/features/social/data/social_models.dart';
import 'package:chessju_app/features/social/data/social_repository.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class ConversationDetailScreen extends ConsumerStatefulWidget {
  const ConversationDetailScreen({super.key, required this.conversationId});

  final String conversationId;

  @override
  ConsumerState<ConversationDetailScreen> createState() =>
      _ConversationDetailScreenState();
}

class _ConversationDetailScreenState
    extends ConsumerState<ConversationDetailScreen> {
  final _messageController = TextEditingController();
  bool _submitting = false;
  String? _message;

  @override
  void initState() {
    super.initState();
    Future.microtask(_markRead);
  }

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final detail = ref.watch(conversationDetailProvider(widget.conversationId));
    final messages = ref.watch(
      conversationMessagesProvider(widget.conversationId),
    );
    final currentUserId = ref.watch(authControllerProvider).user?.id;

    return AsyncValueView(
      value: detail,
      onRetry: () =>
          ref.invalidate(conversationDetailProvider(widget.conversationId)),
      data: (conversation) {
        final other = conversation.otherMember(currentUserId);
        return Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
              child: Row(
                children: [
                  const Icon(Icons.forum_outlined),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          other?.displayName ?? 'Direct conversation',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        if (other != null) Text('@${other.username}'),
                      ],
                    ),
                  ),
                  IconButton(
                    tooltip: 'Refresh',
                    onPressed: _refresh,
                    icon: const Icon(Icons.refresh),
                  ),
                ],
              ),
            ),
            if (_message != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Text(_message!),
              ),
            Expanded(
              child: AsyncValueView(
                value: messages,
                onRetry: () => ref.invalidate(
                  conversationMessagesProvider(widget.conversationId),
                ),
                data: (data) {
                  if (data.items.isEmpty) {
                    return const EmptyView('No messages yet.');
                  }
                  return RefreshIndicator(
                    onRefresh: () async => _refresh(),
                    child: ListView(
                      reverse: true,
                      padding: const EdgeInsets.all(16),
                      children: [
                        for (final message in data.items.reversed)
                          _MessageBubble(
                            message: message,
                            isMine: message.sender.id == currentUserId,
                            onDelete:
                                message.sender.id == currentUserId &&
                                    !message.isDeleted
                                ? () => _deleteMessage(message)
                                : null,
                          ),
                      ],
                    ),
                  );
                },
              ),
            ),
            _MessageComposer(
              controller: _messageController,
              submitting: _submitting,
              onSend: _sendMessage,
            ),
          ],
        );
      },
    );
  }

  void _refresh() {
    ref.invalidate(conversationDetailProvider(widget.conversationId));
    ref.invalidate(conversationMessagesProvider(widget.conversationId));
    ref.invalidate(conversationsProvider);
  }

  Future<void> _sendMessage() async {
    final body = _messageController.text.trim();
    final validation = validateMessageBody(body);
    if (validation != null) {
      setState(() {
        _message = validation;
      });
      return;
    }
    await _submit(() async {
      await ref
          .read(socialRepositoryProvider)
          .sendMessage(conversationId: widget.conversationId, body: body);
      _messageController.clear();
      _message = null;
      _refresh();
      await _markRead();
    });
  }

  Future<void> _deleteMessage(Message message) async {
    await _submit(() async {
      await ref.read(socialRepositoryProvider).deleteMessage(message.id);
      _message = 'Message deleted.';
      _refresh();
    });
  }

  Future<void> _markRead() async {
    try {
      await ref.read(socialRepositoryProvider).markRead(widget.conversationId);
    } catch (_) {
      // Read state is best-effort in the UI; message loading remains authoritative.
    }
  }

  Future<void> _submit(Future<void> Function() action) async {
    setState(() {
      _submitting = true;
      _message = null;
    });
    try {
      await action();
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

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({
    required this.message,
    required this.isMine,
    required this.onDelete,
  });

  final Message message;
  final bool isMine;
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final body = message.isDeleted ? 'Message deleted' : message.body ?? '';
    return Align(
      alignment: isMine ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520),
        child: Card(
          color: isMine
              ? scheme.primaryContainer
              : scheme.surfaceContainerHighest,
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: isMine
                  ? CrossAxisAlignment.end
                  : CrossAxisAlignment.start,
              children: [
                Text(
                  message.sender.username,
                  style: Theme.of(context).textTheme.labelMedium,
                ),
                const SizedBox(height: 4),
                Text(
                  body,
                  style: TextStyle(
                    fontStyle: message.isDeleted
                        ? FontStyle.italic
                        : FontStyle.normal,
                  ),
                ),
                const SizedBox(height: 4),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      message.createdAt,
                      style: Theme.of(context).textTheme.labelSmall,
                    ),
                    if (onDelete != null) ...[
                      const SizedBox(width: 8),
                      IconButton(
                        tooltip: 'Delete message',
                        onPressed: onDelete,
                        icon: const Icon(Icons.delete_outline),
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _MessageComposer extends StatelessWidget {
  const _MessageComposer({
    required this.controller,
    required this.submitting,
    required this.onSend,
  });

  final TextEditingController controller;
  final bool submitting;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: controller,
                minLines: 1,
                maxLines: 4,
                decoration: const InputDecoration(
                  hintText: 'Message',
                  prefixIcon: Icon(Icons.message_outlined),
                ),
              ),
            ),
            const SizedBox(width: 8),
            FilledButton.icon(
              onPressed: submitting ? null : onSend,
              icon: const Icon(Icons.send),
              label: const Text('Send'),
            ),
          ],
        ),
      ),
    );
  }
}
