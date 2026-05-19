import 'package:chessju_app/core/network/api_client.dart';
import 'package:chessju_app/core/network/api_providers.dart';
import 'package:chessju_app/core/pagination/pagination.dart';
import 'package:chessju_app/features/auth/data/auth_models.dart';
import 'package:chessju_app/shared/models/content_models.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final contentRepositoryProvider = Provider<ContentRepository>((ref) {
  return ContentRepository(ref.watch(apiClientProvider));
});

final homeProvider = FutureProvider.autoDispose<HomeContent>((ref) {
  return ref.watch(contentRepositoryProvider).fetchHome();
});

final newsProvider =
    FutureProvider.autoDispose<PaginatedResponse<ArticleSummary>>((ref) {
      return ref.watch(contentRepositoryProvider).fetchNews();
    });

final tournamentListProvider =
    FutureProvider.autoDispose<PaginatedResponse<TournamentSummary>>((ref) {
      return ref.watch(contentRepositoryProvider).fetchTournaments();
    });

final leaderboardProvider =
    FutureProvider.autoDispose<PaginatedResponse<LeaderboardRow>>((ref) {
      return ref.watch(contentRepositoryProvider).fetchLeaderboard();
    });

final notificationsProvider =
    FutureProvider.autoDispose<PaginatedResponse<NotificationItem>>((ref) {
      return ref.watch(contentRepositoryProvider).fetchNotifications();
    });

final unreadNotificationCountProvider = FutureProvider.autoDispose<int>((ref) {
  return ref.watch(contentRepositoryProvider).fetchUnreadNotificationCount();
});

final profileProvider = FutureProvider.autoDispose<CurrentUser>((ref) {
  return ref.watch(contentRepositoryProvider).fetchProfile();
});

class ContentRepository {
  const ContentRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<HomeContent> fetchHome() {
    return _apiClient.get<HomeContent>(
      '/home',
      parse: (data) => HomeContent.fromJson(_asMap(data)),
    );
  }

  Future<PaginatedResponse<ArticleSummary>> fetchNews() {
    return _apiClient.get<PaginatedResponse<ArticleSummary>>(
      '/news',
      queryParameters: const {'limit': 20, 'offset': 0},
      parse: (data) =>
          PaginatedResponse.fromJson(_asMap(data), ArticleSummary.fromJson),
    );
  }

  Future<PaginatedResponse<TournamentSummary>> fetchTournaments() {
    return _apiClient.get<PaginatedResponse<TournamentSummary>>(
      '/tournaments',
      queryParameters: const {'limit': 20, 'offset': 0},
      parse: (data) =>
          PaginatedResponse.fromJson(_asMap(data), TournamentSummary.fromJson),
    );
  }

  Future<PaginatedResponse<LeaderboardRow>> fetchLeaderboard() {
    return _apiClient.get<PaginatedResponse<LeaderboardRow>>(
      '/leaderboard',
      queryParameters: const {'limit': 20, 'offset': 0},
      parse: (data) {
        final json = _asMap(data);
        final rows = (json['rows'] as List? ?? const [])
            .whereType<Map>()
            .map(
              (item) =>
                  LeaderboardRow.fromJson(Map<String, Object?>.from(item)),
            )
            .toList();
        return PaginatedResponse(
          items: rows,
          pagination: Pagination.fromJson({
            'limit': json['limit'],
            'offset': json['offset'],
            'total': json['total'],
            'count': rows.length,
          }),
        );
      },
    );
  }

  Future<PaginatedResponse<NotificationItem>> fetchNotifications() {
    return _apiClient.get<PaginatedResponse<NotificationItem>>(
      '/notifications',
      queryParameters: const {'limit': 20, 'offset': 0},
      parse: (data) =>
          PaginatedResponse.fromJson(_asMap(data), NotificationItem.fromJson),
    );
  }

  Future<int> fetchUnreadNotificationCount() {
    return _apiClient.get<int>(
      '/notifications/unread-count',
      parse: (data) => _asInt(_asMap(data)['unread_count']),
    );
  }

  Future<CurrentUser> fetchProfile() {
    return _apiClient.get<CurrentUser>(
      '/users/me',
      parse: (data) => CurrentUser.fromJson(_asMap(data)),
    );
  }

  Map<String, Object?> _asMap(Object? data) {
    return Map<String, Object?>.from(data as Map? ?? const {});
  }

  int _asInt(Object? value) {
    if (value is int) {
      return value;
    }
    if (value is num) {
      return value.toInt();
    }
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }
}
