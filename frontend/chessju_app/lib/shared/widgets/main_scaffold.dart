import 'package:chessju_app/features/auth/auth_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

class MainScaffold extends ConsumerWidget {
  const MainScaffold({super.key, required this.child});

  final Widget child;

  static const _mainDestinations = [
    _Destination('Home', '/', Icons.home_outlined, Icons.home),
    _Destination(
      'Tournaments',
      '/tournaments',
      Icons.emoji_events_outlined,
      Icons.emoji_events,
    ),
    _Destination('Games', '/games', Icons.grid_on_outlined, Icons.grid_on),
    _Destination(
      'Notifications',
      '/notifications',
      Icons.notifications_outlined,
      Icons.notifications,
    ),
    _Destination('Profile', '/profile', Icons.person_outline, Icons.person),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authControllerProvider);
    final username = authState.user?.profile.username;
    final currentPath = GoRouterState.of(context).uri.path;
    final selectedIndex = _selectedIndexFor(currentPath);

    return LayoutBuilder(
      builder: (context, constraints) {
        final useRail = constraints.maxWidth >= 840;
        final appBar = AppBar(
          title: const Text('ChessJU'),
          actions: [
            IconButton(
              tooltip: 'News',
              onPressed: () => context.go('/news'),
              icon: const Icon(Icons.article_outlined),
            ),
            IconButton(
              tooltip: 'Leaderboard',
              onPressed: () => context.go('/leaderboard'),
              icon: const Icon(Icons.leaderboard_outlined),
            ),
            IconButton(
              tooltip: 'Clock',
              onPressed: () => context.go('/clock'),
              icon: const Icon(Icons.timer_outlined),
            ),
            IconButton(
              tooltip: 'Friends',
              onPressed: () => context.go('/friends'),
              icon: const Icon(Icons.people_outline),
            ),
            if (username != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Center(child: Text('@$username')),
              ),
          ],
        );

        if (useRail) {
          return Scaffold(
            appBar: appBar,
            body: Row(
              children: [
                NavigationRail(
                  selectedIndex: selectedIndex,
                  labelType: NavigationRailLabelType.all,
                  destinations: [
                    for (final destination in _mainDestinations)
                      NavigationRailDestination(
                        icon: Icon(destination.icon),
                        selectedIcon: Icon(destination.selectedIcon),
                        label: Text(destination.label),
                      ),
                  ],
                  onDestinationSelected: (index) {
                    context.go(_mainDestinations[index].path);
                  },
                ),
                const VerticalDivider(width: 1),
                Expanded(child: child),
              ],
            ),
          );
        }

        return Scaffold(
          appBar: appBar,
          body: child,
          bottomNavigationBar: NavigationBar(
            selectedIndex: selectedIndex,
            destinations: [
              for (final destination in _mainDestinations)
                NavigationDestination(
                  icon: Icon(destination.icon),
                  selectedIcon: Icon(destination.selectedIcon),
                  label: destination.label,
                ),
            ],
            onDestinationSelected: (index) {
              context.go(_mainDestinations[index].path);
            },
          ),
        );
      },
    );
  }

  int _selectedIndexFor(String path) {
    if (path.startsWith('/tournaments')) {
      return 1;
    }
    if (path.startsWith('/games')) {
      return 2;
    }
    if (path.startsWith('/notifications')) {
      return 3;
    }
    if (path.startsWith('/profile')) {
      return 4;
    }
    return 0;
  }
}

class _Destination {
  const _Destination(this.label, this.path, this.icon, this.selectedIcon);

  final String label;
  final String path;
  final IconData icon;
  final IconData selectedIcon;
}
