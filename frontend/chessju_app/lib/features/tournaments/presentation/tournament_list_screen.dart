import 'package:chessju_app/core/network/content_repository.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class TournamentListScreen extends ConsumerWidget {
  const TournamentListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tournaments = ref.watch(tournamentListProvider);

    return AsyncValueView(
      value: tournaments,
      data: (data) {
        if (data.items.isEmpty) {
          return const EmptyState('No visible tournaments yet.');
        }

        return RefreshIndicator(
          onRefresh: () => ref.refresh(tournamentListProvider.future),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(
                'Tournaments',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 16),
              for (final item in data.items)
                ContentCard(
                  title: item.title,
                  subtitle:
                      '${item.status} • ${item.startsAt}'
                      '${item.location == null ? '' : ' • ${item.location}'}',
                  trailing: item.spotsRemaining == null
                      ? null
                      : Text('${item.spotsRemaining} spots'),
                ),
            ],
          ),
        );
      },
    );
  }
}
