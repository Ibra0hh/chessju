import 'package:chessju_app/features/auth/presentation/login_screen.dart';
import 'package:chessju_app/features/auth/presentation/register_screen.dart';
import 'package:chessju_app/features/auth/presentation/splash_screen.dart';
import 'package:chessju_app/features/admin/presentation/admin_dashboard_screen.dart';
import 'package:chessju_app/features/clock/presentation/clock_screen.dart';
import 'package:chessju_app/features/games/presentation/game_detail_screen.dart';
import 'package:chessju_app/features/games/presentation/games_screen.dart';
import 'package:chessju_app/features/games/presentation/pgn_import_screen.dart';
import 'package:chessju_app/features/home/presentation/home_screen.dart';
import 'package:chessju_app/features/leaderboard/presentation/leaderboard_screen.dart';
import 'package:chessju_app/features/news/presentation/news_detail_screen.dart';
import 'package:chessju_app/features/news/presentation/news_list_screen.dart';
import 'package:chessju_app/features/notifications/presentation/notifications_screen.dart';
import 'package:chessju_app/features/profile/presentation/profile_screen.dart';
import 'package:chessju_app/features/social/presentation/blocked_users_screen.dart';
import 'package:chessju_app/features/social/presentation/conversation_detail_screen.dart';
import 'package:chessju_app/features/social/presentation/conversations_screen.dart';
import 'package:chessju_app/features/social/presentation/friend_requests_screen.dart';
import 'package:chessju_app/features/social/presentation/friends_screen.dart';
import 'package:chessju_app/features/tournaments/presentation/tournament_detail_screen.dart';
import 'package:chessju_app/features/tournaments/presentation/tournament_list_screen.dart';
import 'package:chessju_app/shared/widgets/main_scaffold.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/splash',
    routes: [
      GoRoute(
        path: '/splash',
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegisterScreen(),
      ),
      ShellRoute(
        builder: (context, state, child) => MainScaffold(child: child),
        routes: [
          GoRoute(path: '/', builder: (context, state) => const HomeScreen()),
          GoRoute(
            path: '/news',
            builder: (context, state) => const NewsListScreen(),
          ),
          GoRoute(
            path: '/news/:slug',
            builder: (context, state) =>
                NewsDetailScreen(slug: state.pathParameters['slug'] ?? ''),
          ),
          GoRoute(
            path: '/tournaments',
            builder: (context, state) => const TournamentListScreen(),
          ),
          GoRoute(
            path: '/tournaments/:slug',
            builder: (context, state) => TournamentDetailScreen(
              slug: state.pathParameters['slug'] ?? '',
            ),
          ),
          GoRoute(
            path: '/leaderboard',
            builder: (context, state) => const LeaderboardScreen(),
          ),
          GoRoute(
            path: '/clock',
            builder: (context, state) => const ClockScreen(),
          ),
          GoRoute(
            path: '/admin',
            builder: (context, state) => const AdminDashboardScreen(),
          ),
          GoRoute(
            path: '/admin/news',
            builder: (context, state) =>
                const AdminDashboardScreen(section: AdminSection.news),
          ),
          GoRoute(
            path: '/admin/announcements',
            builder: (context, state) =>
                const AdminDashboardScreen(section: AdminSection.announcements),
          ),
          GoRoute(
            path: '/admin/time-controls',
            builder: (context, state) =>
                const AdminDashboardScreen(section: AdminSection.timeControls),
          ),
          GoRoute(
            path: '/admin/tournaments',
            builder: (context, state) =>
                const AdminDashboardScreen(section: AdminSection.tournaments),
          ),
          GoRoute(
            path: '/admin/tournaments/:tournamentId',
            builder: (context, state) => AdminTournamentDetailScreen(
              tournamentId: state.pathParameters['tournamentId'] ?? '',
            ),
          ),
          GoRoute(
            path: '/admin/leaderboard',
            builder: (context, state) =>
                const AdminDashboardScreen(section: AdminSection.leaderboard),
          ),
          GoRoute(
            path: '/admin/audit-logs',
            builder: (context, state) =>
                const AdminDashboardScreen(section: AdminSection.auditLogs),
          ),
          GoRoute(
            path: '/admin/lists',
            builder: (context, state) =>
                const AdminDashboardScreen(section: AdminSection.observability),
          ),
          GoRoute(
            path: '/friends',
            builder: (context, state) => const FriendsScreen(),
          ),
          GoRoute(
            path: '/friend-requests',
            builder: (context, state) => const FriendRequestsScreen(),
          ),
          GoRoute(
            path: '/blocks',
            builder: (context, state) => const BlockedUsersScreen(),
          ),
          GoRoute(
            path: '/conversations',
            builder: (context, state) => const ConversationsScreen(),
          ),
          GoRoute(
            path: '/conversations/:conversationId',
            builder: (context, state) => ConversationDetailScreen(
              conversationId: state.pathParameters['conversationId'] ?? '',
            ),
          ),
          GoRoute(
            path: '/games',
            builder: (context, state) => const GamesScreen(),
          ),
          GoRoute(
            path: '/games/import-pgn',
            builder: (context, state) => const PgnImportScreen(),
          ),
          GoRoute(
            path: '/games/:gameId',
            builder: (context, state) =>
                GameDetailScreen(gameId: state.pathParameters['gameId'] ?? ''),
          ),
          GoRoute(
            path: '/notifications',
            builder: (context, state) => const NotificationsScreen(),
          ),
          GoRoute(
            path: '/profile',
            builder: (context, state) => const ProfileScreen(),
          ),
        ],
      ),
    ],
  );
});
