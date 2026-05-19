import 'package:chessju_app/app/router.dart';
import 'package:chessju_app/app/theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class ChessJuApp extends ConsumerWidget {
  const ChessJuApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(appRouterProvider);

    return MaterialApp.router(
      title: 'ChessJU',
      debugShowCheckedModeBanner: false,
      theme: ChessJuTheme.light,
      darkTheme: ChessJuTheme.dark,
      themeMode: ThemeMode.system,
      routerConfig: router,
    );
  }
}
