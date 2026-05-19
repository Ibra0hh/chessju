import 'package:chessju_app/features/auth/auth_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

class MainScaffold extends ConsumerWidget {
  const MainScaffold({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authControllerProvider);
    final username = authState.user?.profile.username;

    return Scaffold(
      appBar: AppBar(
        title: const Text('ChessJU'),
        actions: [
          if (username != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Center(child: Text(username)),
            ),
          IconButton(
            tooltip: 'Logout',
            onPressed: () async {
              await ref.read(authControllerProvider.notifier).logout();
              if (context.mounted) {
                context.go('/login');
              }
            },
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      drawer: const _AppNavigationDrawer(),
      body: child,
    );
  }
}

class _AppNavigationDrawer extends StatelessWidget {
  const _AppNavigationDrawer();

  static const _destinations = [
    _Destination('Home', '/', Icons.home_outlined),
    _Destination('News', '/news', Icons.article_outlined),
    _Destination('Tournaments', '/tournaments', Icons.emoji_events_outlined),
    _Destination('Leaderboard', '/leaderboard', Icons.leaderboard_outlined),
    _Destination('Games', '/games', Icons.grid_on_outlined),
    _Destination(
      'Notifications',
      '/notifications',
      Icons.notifications_outlined,
    ),
    _Destination('Profile', '/profile', Icons.person_outline),
  ];

  @override
  Widget build(BuildContext context) {
    final currentPath = GoRouterState.of(context).uri.path;

    return NavigationDrawer(
      selectedIndex: _destinations.indexWhere(
        (item) => item.path == currentPath,
      ),
      children: [
        const DrawerHeader(
          child: Align(
            alignment: Alignment.bottomLeft,
            child: Text(
              'ChessJU',
              style: TextStyle(fontSize: 28, fontWeight: FontWeight.w700),
            ),
          ),
        ),
        for (final destination in _destinations)
          NavigationDrawerDestination(
            icon: Icon(destination.icon),
            label: Text(destination.label),
            selectedIcon: Icon(destination.icon),
          ),
      ],
      onDestinationSelected: (index) {
        Navigator.of(context).pop();
        context.go(_destinations[index].path);
      },
    );
  }
}

class _Destination {
  const _Destination(this.label, this.path, this.icon);

  final String label;
  final String path;
  final IconData icon;
}
