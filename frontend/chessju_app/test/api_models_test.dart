import 'package:chessju_app/core/errors/api_error.dart';
import 'package:chessju_app/core/pagination/pagination.dart';
import 'package:chessju_app/core/storage/token_storage.dart';
import 'package:chessju_app/features/auth/data/auth_models.dart';
import 'package:chessju_app/shared/models/content_models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('ApiError parses backend error envelope', () {
    final error = ApiError.fromJson({
      'error': {
        'code': 'auth.unauthorized',
        'message': 'Authentication required',
        'details': {'hint': 'login'},
        'request_id': 'req-123',
      },
    });

    expect(error.code, 'auth.unauthorized');
    expect(error.message, 'Authentication required');
    expect(error.details['hint'], 'login');
    expect(error.requestId, 'req-123');
  });

  test('Pagination parses legacy list shape', () {
    final pagination = Pagination.fromJson({
      'items': const [1, 2],
      'limit': 20,
      'offset': 0,
      'total': 42,
    });

    expect(pagination.limit, 20);
    expect(pagination.offset, 0);
    expect(pagination.count, 2);
    expect(pagination.total, 42);
  });

  test('HomeContent parses backend home response', () {
    final home = HomeContent.fromJson({
      'announcements': [
        {
          'id': 'a1',
          'title': 'Round starts',
          'message': 'Round 1 starts at 5 PM',
          'priority': 'important',
        },
      ],
      'latest_news': [
        {'id': 'n1', 'title': 'ChessJU launch', 'slug': 'launch'},
      ],
      'upcoming_tournaments': [
        {
          'id': 't1',
          'title': 'JU Rapid',
          'slug': 'ju-rapid',
          'status': 'registration_open',
          'format': 'swiss',
          'starts_at': '2026-05-20T15:00:00Z',
        },
      ],
      'leaderboard_preview': [
        {
          'rank': 1,
          'user_id': 'u1',
          'username': 'ibrahim',
          'full_name': 'Ibrahim',
          'points': 3,
          'rating': 1200,
        },
      ],
    });

    expect(home.announcements.single.title, 'Round starts');
    expect(home.latestNews.single.slug, 'launch');
    expect(home.upcomingTournaments.single.title, 'JU Rapid');
    expect(home.leaderboardPreview.single.rank, 1);
  });

  test('TournamentDetail parses backend tournament response', () {
    final detail = TournamentDetail.fromJson({
      'id': 't1',
      'title': 'JU Rapid',
      'slug': 'ju-rapid',
      'status': 'registration_open',
      'format': 'swiss',
      'starts_at': '2026-05-20T15:00:00Z',
      'description': 'Weekly rapid tournament',
      'location': 'Student activity center',
      'approved_count': 8,
      'waitlisted_count': 1,
      'max_players': 16,
      'spots_remaining': 8,
      'time_control': {
        'id': 'tc1',
        'name': '10+5',
        'base_seconds': 600,
        'increment_seconds': 5,
        'delay_seconds': 0,
        'type': 'rapid',
      },
      'my_registration': {
        'id': 'r1',
        'tournament_id': 't1',
        'user_id': 'u1',
        'status': 'approved',
        'created_at': '2026-05-19T12:00:00Z',
        'updated_at': '2026-05-19T12:00:00Z',
      },
    });

    expect(detail.title, 'JU Rapid');
    expect(detail.timeControl?.name, '10+5');
    expect(detail.myRegistration?.status, 'approved');
    expect(detail.spotsRemaining, 8);
  });

  test('LeaderboardContent parses leaderboard rows', () {
    final leaderboard = LeaderboardContent.fromJson({
      'season': {
        'id': 's1',
        'name': 'Spring 2026',
        'starts_at': '2026-02-01T00:00:00Z',
        'active': true,
      },
      'generated_at': '2026-05-19T12:00:00Z',
      'rows': [
        {
          'rank': 1,
          'user_id': 'u1',
          'username': 'ibrahim',
          'full_name': 'Ibrahim',
          'points': 4.5,
          'rating': 1210,
          'wins': 4,
          'draws': 1,
          'losses': 0,
          'games_played': 5,
        },
      ],
      'limit': 20,
      'offset': 0,
      'total': 1,
    });

    expect(leaderboard.season?.name, 'Spring 2026');
    expect(leaderboard.rows.single.points, 4.5);
    expect(leaderboard.rows.single.wins, 4);
  });

  test('NotificationItem parses notification response', () {
    final notification = NotificationItem.fromJson({
      'id': 'n1',
      'type': 'message.received',
      'title': 'New message',
      'body': 'You have a new message',
      'read_at': null,
      'created_at': '2026-05-19T12:00:00Z',
    });

    expect(notification.type, 'message.received');
    expect(notification.readAt, isNull);
  });

  test('MemoryTokenStorage saves and clears tokens', () async {
    final storage = MemoryTokenStorage();
    const tokens = AuthTokens(
      accessToken: 'access',
      refreshToken: 'refresh',
      tokenType: 'bearer',
      expiresIn: 900,
    );

    await storage.saveTokens(tokens);
    expect((await storage.readTokens())?.accessToken, 'access');

    await storage.clearTokens();
    expect(await storage.readTokens(), isNull);
  });
}
