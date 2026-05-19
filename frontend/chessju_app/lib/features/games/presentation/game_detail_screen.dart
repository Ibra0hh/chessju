import 'package:chessju_app/core/errors/api_error.dart';
import 'package:chessju_app/features/games/data/game_models.dart';
import 'package:chessju_app/features/games/data/games_repository.dart';
import 'package:chessju_app/features/games/widgets/chess_board_view.dart';
import 'package:chessju_app/features/games/widgets/move_list_view.dart';
import 'package:chessju_app/shared/widgets/async_value_view.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class GameDetailScreen extends ConsumerStatefulWidget {
  const GameDetailScreen({super.key, required this.gameId});

  final String gameId;

  @override
  ConsumerState<GameDetailScreen> createState() => _GameDetailScreenState();
}

class _GameDetailScreenState extends ConsumerState<GameDetailScreen> {
  int _selectedPly = 0;
  bool _requestingAnalysis = false;
  String? _actionMessage;

  @override
  Widget build(BuildContext context) {
    final gameValue = ref.watch(gameDetailProvider(widget.gameId));
    final analysisValue = ref.watch(gameAnalysisProvider(widget.gameId));

    return AsyncValueView(
      value: gameValue,
      onRetry: () => ref.invalidate(gameDetailProvider(widget.gameId)),
      data: (game) {
        final int safeSelectedPly = _selectedPly.clamp(0, game.moves.length);
        final currentFen = safeSelectedPly == 0
            ? game.playableInitialFen
            : game.moves[safeSelectedPly - 1].fenAfter;
        final selectedMove = safeSelectedPly == 0
            ? null
            : game.moves[safeSelectedPly - 1];
        final analysis = analysisValue.when(
          data: (data) => data,
          loading: () => null,
          error: (_, _) => null,
        );
        final report = analysis?.report;
        final evaluations = {
          for (final move in report?.moves ?? const <AnalysisMoveEvaluation>[])
            move.plyNumber: move,
        };

        return RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(gameDetailProvider(widget.gameId));
            ref.invalidate(gameAnalysisProvider(widget.gameId));
          },
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _Header(game: game),
              const SizedBox(height: 16),
              LayoutBuilder(
                builder: (context, constraints) {
                  final wide = constraints.maxWidth >= 900;
                  final board = _BoardPanel(
                    fen: currentFen,
                    lastMoveUci: selectedMove?.uci,
                    selectedPly: safeSelectedPly,
                    totalPlies: game.moves.length,
                    onFirst: () => _selectPly(0),
                    onPrevious: () => _selectPly(safeSelectedPly - 1),
                    onNext: () => _selectPly(safeSelectedPly + 1),
                    onLast: () => _selectPly(game.moves.length),
                  );
                  final side = _SidePanel(
                    game: game,
                    selectedMove: selectedMove,
                    selectedEvaluation: evaluations[safeSelectedPly],
                    selectedPly: safeSelectedPly,
                    evaluations: evaluations,
                    onSelectPly: _selectPly,
                  );

                  if (wide) {
                    return Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SizedBox(width: 480, child: board),
                        const SizedBox(width: 16),
                        Expanded(child: side),
                      ],
                    );
                  }
                  return Column(
                    children: [board, const SizedBox(height: 16), side],
                  );
                },
              ),
              const SizedBox(height: 16),
              _AnalysisSection(
                value: analysisValue,
                selectedEvaluation: evaluations[safeSelectedPly],
                requesting: _requestingAnalysis,
                actionMessage: _actionMessage,
                onRequest: _requestAnalysis,
                onRefresh: () =>
                    ref.invalidate(gameAnalysisProvider(widget.gameId)),
              ),
            ],
          ),
        );
      },
    );
  }

  void _selectPly(int ply) {
    setState(() {
      _selectedPly = ply < 0 ? 0 : ply;
    });
  }

  Future<void> _requestAnalysis() async {
    setState(() {
      _requestingAnalysis = true;
      _actionMessage = null;
    });

    try {
      await ref.read(gamesRepositoryProvider).requestAnalysis(widget.gameId);
      ref.invalidate(gameAnalysisProvider(widget.gameId));
      _actionMessage = 'Analysis request queued.';
    } on ApiException catch (exception) {
      _actionMessage = exception.error.message;
    } finally {
      if (mounted) {
        setState(() {
          _requestingAnalysis = false;
        });
      }
    }
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.game});

  final GameDetail game;

  @override
  Widget build(BuildContext context) {
    final title =
        '${game.whiteName ?? 'White'} vs ${game.blackName ?? 'Black'}';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            StatusChip(game.source),
            if (game.result != null) StatusChip(game.result!),
            if (game.ecoCode != null) StatusChip(game.ecoCode!),
          ],
        ),
      ],
    );
  }
}

class _BoardPanel extends StatelessWidget {
  const _BoardPanel({
    required this.fen,
    required this.lastMoveUci,
    required this.selectedPly,
    required this.totalPlies,
    required this.onFirst,
    required this.onPrevious,
    required this.onNext,
    required this.onLast,
  });

  final String fen;
  final String? lastMoveUci;
  final int selectedPly;
  final int totalPlies;
  final VoidCallback onFirst;
  final VoidCallback onPrevious;
  final VoidCallback onNext;
  final VoidCallback onLast;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            ChessBoardView(fen: fen, lastMoveUci: lastMoveUci),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                IconButton(
                  tooltip: 'First move',
                  onPressed: selectedPly == 0 ? null : onFirst,
                  icon: const Icon(Icons.first_page),
                ),
                IconButton(
                  tooltip: 'Previous move',
                  onPressed: selectedPly == 0 ? null : onPrevious,
                  icon: const Icon(Icons.chevron_left),
                ),
                Text('$selectedPly / $totalPlies'),
                IconButton(
                  tooltip: 'Next move',
                  onPressed: selectedPly >= totalPlies ? null : onNext,
                  icon: const Icon(Icons.chevron_right),
                ),
                IconButton(
                  tooltip: 'Final move',
                  onPressed: selectedPly >= totalPlies ? null : onLast,
                  icon: const Icon(Icons.last_page),
                ),
              ],
            ),
            ExpansionTile(
              tilePadding: EdgeInsets.zero,
              title: const Text('Current FEN'),
              children: [
                SelectableText(
                  fen,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _SidePanel extends StatelessWidget {
  const _SidePanel({
    required this.game,
    required this.selectedMove,
    required this.selectedEvaluation,
    required this.selectedPly,
    required this.evaluations,
    required this.onSelectPly,
  });

  final GameDetail game;
  final GameMove? selectedMove;
  final AnalysisMoveEvaluation? selectedEvaluation;
  final int selectedPly;
  final Map<int, AnalysisMoveEvaluation> evaluations;
  final ValueChanged<int> onSelectPly;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _GameMetadata(game: game),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Moves', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 8),
                MoveListView(
                  moves: game.moves,
                  selectedPly: selectedPly,
                  onSelectPly: onSelectPly,
                  evaluations: evaluations,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        _SelectedMoveCard(move: selectedMove, evaluation: selectedEvaluation),
      ],
    );
  }
}

class _GameMetadata extends StatelessWidget {
  const _GameMetadata({required this.game});

  final GameDetail game;

  @override
  Widget build(BuildContext context) {
    final rows = [
      ('Event', game.event),
      ('Site', game.site),
      ('Date', game.date ?? game.playedAt),
      ('Round', game.round),
      ('Opening', game.openingName),
      ('Time control', game.timeControl),
      ('Created', game.createdAt),
    ].where((row) => row.$2 != null && row.$2!.isNotEmpty).toList();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Game info', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            for (final row in rows)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 96,
                      child: Text(
                        row.$1,
                        style: Theme.of(context).textTheme.labelMedium,
                      ),
                    ),
                    Expanded(child: Text(row.$2!)),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _SelectedMoveCard extends StatelessWidget {
  const _SelectedMoveCard({required this.move, required this.evaluation});

  final GameMove? move;
  final AnalysisMoveEvaluation? evaluation;

  @override
  Widget build(BuildContext context) {
    if (move == null) {
      return const ContentCard(
        title: 'Start position',
        subtitle: 'Use the controls or move list to replay the game.',
        leading: Icon(Icons.flag_outlined),
      );
    }

    final currentMove = move!;
    final details = <String>[
      '${currentMove.side} ${currentMove.san}',
      currentMove.uci,
      if (currentMove.isCheckmate)
        'checkmate'
      else if (currentMove.isCheck)
        'check',
      if (evaluation?.classification != null)
        analysisClassificationLabel(evaluation!.classification),
      if (evaluation?.evaluationAfter != null)
        'Eval ${evaluation!.evaluationAfter!.label}',
      if (evaluation?.centipawnLoss != null)
        '${evaluation!.centipawnLoss} cp loss',
    ];

    return ContentCard(
      title: 'Move ${currentMove.moveNumber}: ${currentMove.san}',
      subtitle: details.join(' | '),
      leading: const Icon(Icons.play_arrow_outlined),
    );
  }
}

class _AnalysisSection extends StatelessWidget {
  const _AnalysisSection({
    required this.value,
    required this.selectedEvaluation,
    required this.requesting,
    required this.actionMessage,
    required this.onRequest,
    required this.onRefresh,
  });

  final AsyncValue<GameAnalysisState> value;
  final AnalysisMoveEvaluation? selectedEvaluation;
  final bool requesting;
  final String? actionMessage;
  final VoidCallback onRequest;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final data = value.when(
      data: (data) => data,
      loading: () => null,
      error: (_, _) => null,
    );
    final report = data?.report;
    final job = data?.job;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Analysis',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                IconButton(
                  tooltip: 'Refresh analysis',
                  onPressed: onRefresh,
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ),
            if (value.isLoading) const LinearProgressIndicator(),
            if (actionMessage != null) ...[
              const SizedBox(height: 8),
              Text(actionMessage!),
            ],
            const SizedBox(height: 8),
            if (report != null)
              _AnalysisReportView(
                report: report,
                selectedEvaluation: selectedEvaluation,
              )
            else if (job != null)
              _AnalysisJobView(job: job)
            else
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('No completed analysis exists for this game yet.'),
                  const SizedBox(height: 12),
                  PrimaryButton(
                    label: 'Request analysis',
                    icon: Icons.psychology_outlined,
                    loading: requesting,
                    onPressed: onRequest,
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

class _AnalysisJobView extends StatelessWidget {
  const _AnalysisJobView({required this.job});

  final AnalysisJob job;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            StatusChip(job.status),
            StatusChip(job.engineName),
            if (job.depth != null) StatusChip('depth ${job.depth}'),
          ],
        ),
        if (job.errorMessage != null) ...[
          const SizedBox(height: 8),
          Text(job.errorMessage!),
        ],
      ],
    );
  }
}

class _AnalysisReportView extends StatelessWidget {
  const _AnalysisReportView({
    required this.report,
    required this.selectedEvaluation,
  });

  final AnalysisReport report;
  final AnalysisMoveEvaluation? selectedEvaluation;

  @override
  Widget build(BuildContext context) {
    final whiteSummary = _summarySide(report.summary['white']);
    final blackSummary = _summarySide(report.summary['black']);
    final totalMoves = report.summary['total_moves']?.toString();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            if (report.whiteAccuracy != null)
              StatusChip('White ${report.whiteAccuracy!.toStringAsFixed(1)}%'),
            if (report.blackAccuracy != null)
              StatusChip('Black ${report.blackAccuracy!.toStringAsFixed(1)}%'),
            if (totalMoves != null) StatusChip('$totalMoves moves'),
            if (report.finalEvaluation != null)
              StatusChip('Final ${report.finalEvaluation!.label}'),
          ],
        ),
        const SizedBox(height: 12),
        _ClassificationCounts(title: 'White', counts: whiteSummary),
        const SizedBox(height: 8),
        _ClassificationCounts(title: 'Black', counts: blackSummary),
        if (selectedEvaluation != null) ...[
          const SizedBox(height: 16),
          Text('Selected move', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          _EvaluationDetails(evaluation: selectedEvaluation!),
        ],
      ],
    );
  }

  Map<String, int> _summarySide(Object? value) {
    if (value is! Map) {
      return const {};
    }
    return Map<String, Object?>.from(
      value,
    ).map((key, item) => MapEntry(key, _asInt(item)));
  }

  int _asInt(Object? value) {
    if (value is int) {
      return value;
    }
    if (value is num) {
      return value.toInt();
    }
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }
}

class _ClassificationCounts extends StatelessWidget {
  const _ClassificationCounts({required this.title, required this.counts});

  final String title;
  final Map<String, int> counts;

  @override
  Widget build(BuildContext context) {
    if (counts.isEmpty) {
      return Text('$title: no summary counts yet.');
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.labelLarge),
        const SizedBox(height: 4),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final entry in counts.entries)
              Chip(
                label: Text(
                  '${analysisClassificationLabel(entry.key)}: ${entry.value}',
                ),
              ),
          ],
        ),
      ],
    );
  }
}

class _EvaluationDetails extends StatelessWidget {
  const _EvaluationDetails({required this.evaluation});

  final AnalysisMoveEvaluation evaluation;

  @override
  Widget build(BuildContext context) {
    final lines = [
      'Classification: ${analysisClassificationLabel(evaluation.classification)}',
      if (evaluation.centipawnLoss != null)
        'Centipawn loss: ${evaluation.centipawnLoss}',
      if (evaluation.evaluationBefore != null)
        'Before: ${evaluation.evaluationBefore!.label}',
      if (evaluation.evaluationAfter != null)
        'After: ${evaluation.evaluationAfter!.label}',
      if (evaluation.bestMoveSan != null) 'Best: ${evaluation.bestMoveSan}',
      if (evaluation.bestMoveUci != null) 'Best UCI: ${evaluation.bestMoveUci}',
      if (evaluation.principalVariation.isNotEmpty)
        'PV: ${evaluation.principalVariation.join(' ')}',
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [for (final line in lines) Text(line)],
    );
  }
}
