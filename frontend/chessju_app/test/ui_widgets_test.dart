import 'package:chessju_app/core/storage/token_storage.dart';
import 'package:chessju_app/features/auth/presentation/login_screen.dart';
import 'package:chessju_app/features/games/presentation/pgn_import_screen.dart';
import 'package:chessju_app/shared/widgets/content_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('Login form validates required fields', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          tokenStorageProvider.overrideWithValue(MemoryTokenStorage()),
        ],
        child: const MaterialApp(home: LoginScreen()),
      ),
    );

    await tester.tap(find.text('Login'));
    await tester.pump();

    expect(find.text('Enter an email'), findsOneWidget);
    expect(find.text('Enter a password'), findsOneWidget);
  });

  testWidgets('ErrorView displays message', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: ErrorView(message: 'Something failed')),
      ),
    );

    expect(find.text('Something failed'), findsOneWidget);
  });

  testWidgets('EmptyView displays message', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: EmptyView('Nothing here'))),
    );

    expect(find.text('Nothing here'), findsOneWidget);
  });

  testWidgets('PGN paste form validates non-empty input', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          tokenStorageProvider.overrideWithValue(MemoryTokenStorage()),
        ],
        child: const MaterialApp(home: Scaffold(body: PgnImportScreen())),
      ),
    );

    await tester.tap(find.text('Import game'));
    await tester.pump();

    expect(find.text('Paste a PGN game first'), findsOneWidget);
  });
}
