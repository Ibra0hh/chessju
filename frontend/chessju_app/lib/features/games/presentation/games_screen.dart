import 'package:chessju_app/features/games/data/games_repository.dart';
import 'package:chessju_app/shared/models/content_models.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

class GamesScreen extends ConsumerStatefulWidget {
  const GamesScreen({super.key});

  @override
  ConsumerState<GamesScreen> createState() => _GamesScreenState();
}

class _GamesScreenState extends ConsumerState<GamesScreen> {
  String? _source;

  @override
  Widget build(BuildContext context) {
    final games = ref.watch(gameListProvider(_source));

    return AsyncValueView(
      value: games,
      onRetry: () => ref.invalidate(gameListProvider(_source)),
      data: (data) {
        return RefreshIndicator(
          onRefresh: () => ref.refresh(gameListProvider(_source).future),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      'Games',
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                  ),
                  FilledButton.icon(
                    onPressed: () => context.go('/games/import-pgn'),
                    icon: const Icon(Icons.upload_file_outlined),
                    label: const Text('Import PGN'),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              _SourceFilter(
                selected: _source,
                onChanged: (value) {
                  setState(() {
                    _source = value;
                  });
                },
              ),
              const SizedBox(height: 16),
              if (data.items.isEmpty)
                EmptyView(
                  _source == null
                      ? 'No games yet. Import a PGN to start building your library.'
                      : 'No games match this filter.',
                  icon: Icons.grid_on_outlined,
                )
              else
                for (final game in data.items)
                  ContentCard(
                    title:
                        '${game.whiteName ?? 'White'} vs ${game.blackName ?? 'Black'}',
                    subtitle: _subtitleFor(game),
                    leading: const Icon(Icons.grid_on_outlined),
                    trailing: Text('${game.movesCount} plies'),
                    onTap: () => context.go('/games/${game.id}'),
                  ),
            ],
          ),
        );
      },
    );
  }

  String _subtitleFor(GameSummary game) {
    final parts = [
      game.source,
      game.result ?? '*',
      if (game.event != null) game.event,
      if (game.ecoCode != null || game.openingName != null)
        [
          game.ecoCode,
          game.openingName,
        ].whereType<String>().where((part) => part.isNotEmpty).join(' '),
      game.playedAt ?? game.createdAt,
    ];
    return parts
        .whereType<String>()
        .where((part) => part.isNotEmpty)
        .join(' | ');
  }
}

class _SourceFilter extends StatelessWidget {
  const _SourceFilter({required this.selected, required this.onChanged});

  final String? selected;
  final ValueChanged<String?> onChanged;

  static const _options = <(String, String)>[
    ('All', 'all'),
    ('Tournament', 'tournament'),
    ('PGN', 'pgn_upload'),
    ('Chess.com', 'chesscom_import'),
  ];

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: SegmentedButton<String>(
        segments: [
          for (final option in _options)
            ButtonSegment<String>(value: option.$2, label: Text(option.$1)),
        ],
        selected: {selected ?? 'all'},
        onSelectionChanged: (values) {
          final value = values.single;
          onChanged(value == 'all' ? null : value);
        },
      ),
    );
  }
}
