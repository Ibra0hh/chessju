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

    return AsyncValueView(
      value: leaderboard,
      data: (data) {
        if (data.items.isEmpty) {
          return const EmptyState('Leaderboard has not been generated yet.');
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
              const SizedBox(height: 16),
              for (final row in data.items)
                ContentCard(
                  title: '#${row.rank} ${row.username}',
                  subtitle: '${row.fullName} • ${row.points} pts',
                  trailing: Text('${row.rating}'),
                ),
            ],
          ),
        );
      },
    );
  }
}
