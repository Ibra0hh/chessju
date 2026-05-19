import 'package:chessju_app/app/app.dart';
import 'package:chessju_app/core/storage/token_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

void main() {
  testWidgets('app starts at splash screen', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          tokenStorageProvider.overrideWithValue(MemoryTokenStorage()),
        ],
        child: const ChessJuApp(),
      ),
    );

    expect(find.text('ChessJU'), findsOneWidget);
  });
}
