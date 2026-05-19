import 'package:flutter/material.dart';

class ChessBoardView extends StatelessWidget {
  const ChessBoardView({super.key, required this.fen, this.lastMoveUci});

  final String fen;
  final String? lastMoveUci;

  @override
  Widget build(BuildContext context) {
    final pieces = _piecesFromFen(fen);
    final highlightedSquares = _highlightedSquares(lastMoveUci);
    final scheme = Theme.of(context).colorScheme;

    return AspectRatio(
      aspectRatio: 1,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: DecoratedBox(
          decoration: BoxDecoration(
            border: Border.all(color: scheme.outlineVariant),
          ),
          child: GridView.builder(
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 8,
            ),
            itemCount: 64,
            itemBuilder: (context, index) {
              final row = index ~/ 8;
              final col = index % 8;
              final isLight = (row + col).isEven;
              final square = _squareFor(row, col);
              final highlighted = highlightedSquares.contains(square);
              final piece = pieces[index];

              return ColoredBox(
                color: highlighted
                    ? scheme.tertiaryContainer
                    : isLight
                    ? const Color(0xFFE7E9DA)
                    : const Color(0xFF4B7C74),
                child: Center(
                  child: Text(
                    _unicodePiece(piece),
                    style: TextStyle(
                      fontSize: 34,
                      height: 1,
                      color: _pieceColor(context, piece),
                      fontWeight: FontWeight.w600,
                      shadows: const [
                        Shadow(
                          color: Color(0x66000000),
                          offset: Offset(0, 1),
                          blurRadius: 2,
                        ),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  List<String> _piecesFromFen(String fen) {
    final placement = fen.split(' ').first;
    final pieces = <String>[];

    for (final codeUnit in placement.codeUnits) {
      final char = String.fromCharCode(codeUnit);
      if (char == '/') {
        continue;
      }
      final emptyCount = int.tryParse(char);
      if (emptyCount != null) {
        pieces.addAll(List.filled(emptyCount, ''));
      } else {
        pieces.add(char);
      }
    }

    if (pieces.length < 64) {
      pieces.addAll(List.filled(64 - pieces.length, ''));
    }
    return pieces.take(64).toList();
  }

  Set<String> _highlightedSquares(String? uci) {
    if (uci == null || uci.length < 4) {
      return const {};
    }
    return {uci.substring(0, 2), uci.substring(2, 4)};
  }

  String _squareFor(int row, int col) {
    final file = String.fromCharCode('a'.codeUnitAt(0) + col);
    final rank = 8 - row;
    return '$file$rank';
  }

  String _unicodePiece(String piece) {
    return switch (piece) {
      'K' => '♔',
      'Q' => '♕',
      'R' => '♖',
      'B' => '♗',
      'N' => '♘',
      'P' => '♙',
      'k' => '♚',
      'q' => '♛',
      'r' => '♜',
      'b' => '♝',
      'n' => '♞',
      'p' => '♟',
      _ => '',
    };
  }

  Color _pieceColor(BuildContext context, String piece) {
    if (piece.isEmpty) {
      return Colors.transparent;
    }
    final scheme = Theme.of(context).colorScheme;
    return piece == piece.toUpperCase() ? scheme.surface : scheme.onSurface;
  }
}
