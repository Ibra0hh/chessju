import 'package:chessju_app/core/network/content_repository.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class GamesScreen extends ConsumerWidget {
  const GamesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final games = ref.watch(gamesProvider);

    return AsyncValueView(
      value: games,
      onRetry: () => ref.invalidate(gamesProvider),
      data: (data) {
        if (data.items.isEmpty) {
          return const EmptyView(
            'No games yet. PGN replay and analysis UI will build on this list.',
          );
        }

        return RefreshIndicator(
          onRefresh: () => ref.refresh(gamesProvider.future),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text('Games', style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 16),
              for (final game in data.items)
                ContentCard(
                  title:
                      '${game.whiteName ?? 'White'} vs ${game.blackName ?? 'Black'}',
                  subtitle:
                      '${game.source} | ${game.result ?? '*'} | ${game.playedAt ?? game.createdAt}',
                  leading: const Icon(Icons.grid_on_outlined),
                  trailing: Text('${game.movesCount} plies'),
                ),
            ],
          ),
        );
      },
    );
  }
}
