import 'package:chessju_app/core/network/content_repository.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class LeaderboardScreen extends ConsumerWidget {
  const LeaderboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final leaderboard = ref.watch(leaderboardProvider);
    final seasons = ref.watch(leaderboardSeasonsProvider);

    return AsyncValueView(
      value: leaderboard,
      onRetry: () => ref.invalidate(leaderboardProvider),
      data: (data) {
        if (data.rows.isEmpty) {
          return const EmptyView('Leaderboard has not been generated yet.');
        }

        return RefreshIndicator(
          onRefresh: () => ref.refresh(leaderboardProvider.future),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(
                'JU Leaderboard',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 8),
              Text(
                data.season?.name ?? 'All-time leaderboard',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              if (data.generatedAt != null)
                Text('Generated ${data.generatedAt}'),
              const SizedBox(height: 12),
              seasons.when(
                data: (value) => value.items.isEmpty
                    ? const SizedBox.shrink()
                    : Wrap(
                        spacing: 8,
                        children: [
                          for (final season in value.items.take(6))
                            StatusChip(
                              season.active
                                  ? '${season.name} active'
                                  : season.name,
                            ),
                        ],
                      ),
                loading: () => const SizedBox.shrink(),
                error: (_, _) => const SizedBox.shrink(),
              ),
              const SizedBox(height: 16),
              for (final row in data.rows)
                ContentCard(
                  title: '#${row.rank} ${row.username}',
                  subtitle:
                      '${row.fullName} | ${row.points} pts | W ${row.wins} D ${row.draws} L ${row.losses}',
                  leading: const Icon(Icons.leaderboard_outlined),
                  trailing: Text('${row.gamesPlayed} games'),
                ),
            ],
          ),
        );
      },
    );
  }
}
