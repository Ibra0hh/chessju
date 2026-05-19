import 'package:chessju_app/core/network/content_repository.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final home = ref.watch(homeProvider);

    return AsyncValueView(
      value: home,
      onRetry: () => ref.invalidate(homeProvider),
      data: (data) => RefreshIndicator(
        onRefresh: () => ref.refresh(homeProvider.future),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text('Home', style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 16),
            _Section(
              title: 'Announcements',
              emptyMessage: 'No active announcements.',
              children: [
                for (final item in data.announcements)
                  ContentCard(
                    title: item.title,
                    subtitle: item.message,
                    leading: const Icon(Icons.campaign_outlined),
                    trailing: StatusChip(item.priority),
                  ),
              ],
            ),
            _Section(
              title: 'Latest news',
              emptyMessage: 'No published news yet.',
              trailing: TextButton(
                onPressed: () => context.go('/news'),
                child: const Text('View all'),
              ),
              children: [
                for (final item in data.latestNews)
                  ContentCard(
                    title: item.title,
                    subtitle: item.summary,
                    leading: const Icon(Icons.article_outlined),
                    onTap: () => context.go('/news/${item.slug}'),
                  ),
              ],
            ),
            _Section(
              title: 'Upcoming tournaments',
              emptyMessage: 'No upcoming tournaments.',
              trailing: TextButton(
                onPressed: () => context.go('/tournaments'),
                child: const Text('View all'),
              ),
              children: [
                for (final item in data.upcomingTournaments)
                  ContentCard(
                    title: item.title,
                    subtitle: '${item.status} | ${item.startsAt}',
                    leading: const Icon(Icons.emoji_events_outlined),
                    trailing: item.spotsRemaining == null
                        ? null
                        : Text('${item.spotsRemaining} spots'),
                    onTap: () => context.go('/tournaments/${item.slug}'),
                  ),
              ],
            ),
            _Section(
              title: 'JU leaderboard',
              emptyMessage: 'Leaderboard has not been generated yet.',
              trailing: TextButton(
                onPressed: () => context.go('/leaderboard'),
                child: const Text('Open'),
              ),
              children: [
                for (final row in data.leaderboardPreview)
                  ContentCard(
                    title: '#${row.rank} ${row.username}',
                    subtitle: '${row.points} pts | ${row.rating}',
                    leading: const Icon(Icons.leaderboard_outlined),
                    onTap: () => context.go('/leaderboard'),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({
    required this.title,
    required this.emptyMessage,
    required this.children,
    this.trailing,
  });

  final String title;
  final String emptyMessage;
  final List<Widget> children;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              trailing ?? const SizedBox.shrink(),
            ],
          ),
          const SizedBox(height: 8),
          if (children.isEmpty) EmptyView(emptyMessage) else ...children,
        ],
      ),
    );
  }
}
