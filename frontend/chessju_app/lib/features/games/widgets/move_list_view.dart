import 'package:chessju_app/features/games/data/game_models.dart';
import 'package:flutter/material.dart';

class MoveListView extends StatelessWidget {
  const MoveListView({
    super.key,
    required this.moves,
    required this.selectedPly,
    required this.onSelectPly,
    this.evaluations = const {},
  });

  final List<GameMove> moves;
  final int selectedPly;
  final ValueChanged<int> onSelectPly;
  final Map<int, AnalysisMoveEvaluation> evaluations;

  @override
  Widget build(BuildContext context) {
    if (moves.isEmpty) {
      return const Text('No moves available.');
    }

    final rows = <Widget>[];
    for (var index = 0; index < moves.length; index += 2) {
      final white = moves[index];
      final black = index + 1 < moves.length ? moves[index + 1] : null;
      rows.add(
        _MoveRow(
          number: white.moveNumber,
          white: white,
          black: black,
          whiteEvaluation: evaluations[white.plyNumber],
          blackEvaluation: black == null ? null : evaluations[black.plyNumber],
          selectedPly: selectedPly,
          onSelectPly: onSelectPly,
        ),
      );
    }

    return Column(children: rows);
  }
}

class _MoveRow extends StatelessWidget {
  const _MoveRow({
    required this.number,
    required this.white,
    required this.black,
    required this.whiteEvaluation,
    required this.blackEvaluation,
    required this.selectedPly,
    required this.onSelectPly,
  });

  final int number;
  final GameMove white;
  final GameMove? black;
  final AnalysisMoveEvaluation? whiteEvaluation;
  final AnalysisMoveEvaluation? blackEvaluation;
  final int selectedPly;
  final ValueChanged<int> onSelectPly;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          SizedBox(
            width: 32,
            child: Text(
              '$number.',
              style: Theme.of(context).textTheme.labelMedium,
            ),
          ),
          Expanded(
            child: _MoveButton(
              move: white,
              evaluation: whiteEvaluation,
              selected: selectedPly == white.plyNumber,
              onPressed: () => onSelectPly(white.plyNumber),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: black == null
                ? const SizedBox.shrink()
                : _MoveButton(
                    move: black!,
                    evaluation: blackEvaluation,
                    selected: selectedPly == black!.plyNumber,
                    onPressed: () => onSelectPly(black!.plyNumber),
                  ),
          ),
        ],
      ),
    );
  }
}

class _MoveButton extends StatelessWidget {
  const _MoveButton({
    required this.move,
    required this.evaluation,
    required this.selected,
    required this.onPressed,
  });

  final GameMove move;
  final AnalysisMoveEvaluation? evaluation;
  final bool selected;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final classification = evaluation?.classification;

    return TextButton(
      style: TextButton.styleFrom(
        alignment: Alignment.centerLeft,
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        backgroundColor: selected
            ? scheme.primaryContainer
            : _classificationColor(context, classification),
        foregroundColor: selected
            ? scheme.onPrimaryContainer
            : scheme.onSurfaceVariant,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      onPressed: onPressed,
      child: Row(
        children: [
          Flexible(
            child: Text(
              move.san,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
          if (classification != null) ...[
            const SizedBox(width: 6),
            Icon(_classificationIcon(classification), size: 14),
          ],
        ],
      ),
    );
  }

  Color _classificationColor(BuildContext context, String? classification) {
    final scheme = Theme.of(context).colorScheme;
    return switch (classification) {
      'blunder' => scheme.errorContainer,
      'mistake' => scheme.errorContainer.withValues(alpha: 0.55),
      'inaccuracy' => scheme.tertiaryContainer.withValues(alpha: 0.65),
      'best' || 'excellent' => scheme.secondaryContainer.withValues(alpha: 0.7),
      _ => Colors.transparent,
    };
  }

  IconData _classificationIcon(String classification) {
    return switch (classification) {
      'best' => Icons.check_circle_outline,
      'excellent' => Icons.star_border,
      'good' => Icons.thumb_up_alt_outlined,
      'inaccuracy' => Icons.error_outline,
      'mistake' => Icons.warning_amber_outlined,
      'blunder' => Icons.dangerous_outlined,
      'forced' => Icons.route_outlined,
      _ => Icons.help_outline,
    };
  }
}
