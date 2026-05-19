import 'package:chessju_app/core/network/content_repository.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final home = ref.watch(homeProvider);

    return AsyncValueView(
      value: home,
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
                    trailing: Text(item.priority),
                  ),
              ],
            ),
            _Section(
              title: 'Latest news',
              emptyMessage: 'No published news yet.',
              children: [
                for (final item in data.latestNews)
                  ContentCard(title: item.title, subtitle: item.summary),
              ],
            ),
            _Section(
              title: 'Upcoming tournaments',
              emptyMessage: 'No upcoming tournaments.',
              children: [
                for (final item in data.upcomingTournaments)
                  ContentCard(
                    title: item.title,
                    subtitle: '${item.status} • ${item.startsAt}',
                  ),
              ],
            ),
            _Section(
              title: 'JU leaderboard',
              emptyMessage: 'Leaderboard has not been generated yet.',
              children: [
                for (final row in data.leaderboardPreview)
                  ContentCard(
                    title: '#${row.rank} ${row.username}',
                    subtitle: '${row.points} pts • ${row.rating}',
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
  });

  final String title;
  final String emptyMessage;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          if (children.isEmpty) EmptyState(emptyMessage) else ...children,
        ],
      ),
    );
  }
}
