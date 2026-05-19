import 'package:chessju_app/core/network/content_repository.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class NewsListScreen extends ConsumerWidget {
  const NewsListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final news = ref.watch(newsProvider);

    return AsyncValueView(
      value: news,
      data: (data) {
        if (data.items.isEmpty) {
          return const EmptyState('No published news yet.');
        }

        return RefreshIndicator(
          onRefresh: () => ref.refresh(newsProvider.future),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text('News', style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 16),
              for (final item in data.items)
                ContentCard(title: item.title, subtitle: item.summary),
            ],
          ),
        );
      },
    );
  }
}
