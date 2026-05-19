import 'package:chessju_app/core/errors/api_error.dart';
import 'package:chessju_app/core/pagination/pagination.dart';
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
}
