import 'package:chessju_app/core/network/content_repository.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class NewsDetailScreen extends ConsumerWidget {
  const NewsDetailScreen({super.key, required this.slug});

  final String slug;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final article = ref.watch(newsDetailProvider(slug));

    return AsyncValueView(
      value: article,
      onRetry: () => ref.invalidate(newsDetailProvider(slug)),
      data: (data) => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(data.title, style: Theme.of(context).textTheme.headlineMedium),
          if (data.publishedAt != null) ...[
            const SizedBox(height: 8),
            Text(data.publishedAt!),
          ],
          if (data.summary != null) ...[
            const SizedBox(height: 16),
            Text(data.summary!, style: Theme.of(context).textTheme.titleMedium),
          ],
          const SizedBox(height: 24),
          SelectableText(data.bodyMarkdown),
        ],
      ),
    );
  }
}
