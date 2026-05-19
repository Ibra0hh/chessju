import 'package:chessju_app/core/storage/token_storage.dart';
import 'package:chessju_app/features/admin/data/admin_models.dart';
import 'package:chessju_app/features/admin/presentation/admin_dashboard_screen.dart';
import 'package:chessju_app/features/auth/presentation/login_screen.dart';
import 'package:chessju_app/features/clock/data/clock_models.dart';
import 'package:chessju_app/features/clock/presentation/clock_screen.dart';
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

  testWidgets('Clock screen initial setup renders', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          tokenStorageProvider.overrideWithValue(MemoryTokenStorage()),
        ],
        child: const MaterialApp(home: Scaffold(body: ClockScreen())),
      ),
    );

    expect(find.text('Chess Clock'), findsOneWidget);
    expect(find.text('Time controls'), findsOneWidget);
    expect(find.text('5 + 0'), findsOneWidget);
  });

  testWidgets('Clock status labels render', (tester) async {
    final session = ClockSession.fromJson({
      'id': 'c1',
      'base_seconds': 300,
      'increment_seconds': 0,
      'delay_seconds': 0,
      'white_remaining_ms': 300000,
      'black_remaining_ms': 300000,
      'active_color': 'white',
      'status': 'running',
      'created_by': 'u1',
      'created_at': '2026-05-19T12:00:00Z',
      'updated_at': '2026-05-19T12:00:00Z',
    });

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: ClockTimerPanel(
              session: session,
              clockTheme: 'teal',
              soundEnabled: true,
              fullScreenPlaceholder: false,
              submitting: false,
              onStart: () {},
              onPause: () {},
              onResume: () {},
              onSwitchTurn: () {},
              onFlag: () {},
              onComplete: () {},
              onReset: () {},
              onCancel: () {},
              onAdjust: (_, _) {},
              onSoundChanged: (_) {},
              onFullScreenChanged: (_) {},
              onThemeChanged: (_) {},
            ),
          ),
        ),
      ),
    );

    expect(find.text('running'), findsOneWidget);
    expect(find.text('white to move'), findsOneWidget);
    expect(find.text('5:00'), findsWidgets);
  });

  testWidgets('Admin dashboard overview renders sections', (tester) async {
    const admin = AdminIdentity(
      id: 'a1',
      email: 'admin@example.com',
      roles: ['admin'],
      username: 'admin_user',
      fullName: 'Admin User',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: AdminOverviewContent(admin: admin, onOpen: (_) {}),
          ),
        ),
      ),
    );

    expect(find.text('Admin Dashboard'), findsOneWidget);
    expect(find.text('News'), findsOneWidget);
    expect(find.text('Tournaments'), findsOneWidget);
    expect(find.text('Audit Logs'), findsOneWidget);
  });
}
