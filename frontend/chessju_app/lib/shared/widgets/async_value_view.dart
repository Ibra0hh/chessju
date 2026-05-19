import 'package:chessju_app/core/errors/api_error.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class AsyncValueView<T> extends StatelessWidget {
  const AsyncValueView({
    super.key,
    required this.value,
    required this.data,
    this.onRetry,
  });

  final AsyncValue<T> value;
  final Widget Function(T data) data;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return value.when(
      data: data,
      loading: () => const LoadingView(),
      error: (error, stackTrace) =>
          ErrorView(message: _messageFor(error), onRetry: onRetry),
    );
  }

  String _messageFor(Object error) {
    if (error is ApiException) {
      return error.error.message;
    }
    return 'Unable to load data.';
  }
}
