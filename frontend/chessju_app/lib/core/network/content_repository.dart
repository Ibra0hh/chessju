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

final newsDetailProvider = FutureProvider.autoDispose
    .family<ArticleDetail, String>((ref, slug) {
      return ref.watch(contentRepositoryProvider).fetchNewsDetail(slug);
    });

final tournamentListProvider =
    FutureProvider.autoDispose<PaginatedResponse<TournamentSummary>>((ref) {
      return ref.watch(contentRepositoryProvider).fetchTournaments();
    });

final tournamentDetailProvider = FutureProvider.autoDispose
    .family<TournamentDetail, String>((ref, slug) {
      return ref.watch(contentRepositoryProvider).fetchTournamentDetail(slug);
    });

final tournamentRoundsProvider = FutureProvider.autoDispose
    .family<PaginatedResponse<RoundSummary>, String>((ref, slug) {
      return ref.watch(contentRepositoryProvider).fetchTournamentRounds(slug);
    });

final tournamentStandingsProvider = FutureProvider.autoDispose
    .family<List<StandingRow>, String>((ref, slug) {
      return ref
          .watch(contentRepositoryProvider)
          .fetchTournamentStandings(slug);
    });

final leaderboardProvider = FutureProvider.autoDispose<LeaderboardContent>((
  ref,
) {
  return ref.watch(contentRepositoryProvider).fetchLeaderboard();
});

final leaderboardSeasonsProvider =
    FutureProvider.autoDispose<PaginatedResponse<SeasonSummary>>((ref) {
      return ref.watch(contentRepositoryProvider).fetchLeaderboardSeasons();
    });

final gamesProvider =
    FutureProvider.autoDispose<PaginatedResponse<GameSummary>>((ref) {
      return ref.watch(contentRepositoryProvider).fetchGames();
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

  Future<ArticleDetail> fetchNewsDetail(String slug) {
    return _apiClient.get<ArticleDetail>(
      '/news/$slug',
      parse: (data) => ArticleDetail.fromJson(_asMap(data)),
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

  Future<TournamentDetail> fetchTournamentDetail(String slug) {
    return _apiClient.get<TournamentDetail>(
      '/tournaments/$slug',
      parse: (data) => TournamentDetail.fromJson(_asMap(data)),
    );
  }

  Future<TournamentRegistration> registerForTournament(String tournamentId) {
    return _apiClient.post<TournamentRegistration>(
      '/tournaments/$tournamentId/register',
      parse: (data) => TournamentRegistration.fromJson(_asMap(data)),
    );
  }

  Future<TournamentRegistration> cancelTournamentRegistration(
    String tournamentId,
  ) {
    return _apiClient.delete<TournamentRegistration>(
      '/tournaments/$tournamentId/registration',
      parse: (data) => TournamentRegistration.fromJson(_asMap(data)),
    );
  }

  Future<PaginatedResponse<RoundSummary>> fetchTournamentRounds(String slug) {
    return _apiClient.get<PaginatedResponse<RoundSummary>>(
      '/tournaments/$slug/rounds',
      queryParameters: const {'limit': 50, 'offset': 0},
      parse: (data) =>
          PaginatedResponse.fromJson(_asMap(data), RoundSummary.fromJson),
    );
  }

  Future<List<StandingRow>> fetchTournamentStandings(String slug) {
    return _apiClient.get<List<StandingRow>>(
      '/tournaments/$slug/standings',
      parse: (data) => _list(_asMap(data)['items'], StandingRow.fromJson),
    );
  }

  Future<LeaderboardContent> fetchLeaderboard() {
    return _apiClient.get<LeaderboardContent>(
      '/leaderboard',
      queryParameters: const {'limit': 20, 'offset': 0},
      parse: (data) => LeaderboardContent.fromJson(_asMap(data)),
    );
  }

  Future<PaginatedResponse<SeasonSummary>> fetchLeaderboardSeasons() {
    return _apiClient.get<PaginatedResponse<SeasonSummary>>(
      '/leaderboard/seasons',
      queryParameters: const {'limit': 20, 'offset': 0},
      parse: (data) =>
          PaginatedResponse.fromJson(_asMap(data), SeasonSummary.fromJson),
    );
  }

  Future<PaginatedResponse<GameSummary>> fetchGames() {
    return _apiClient.get<PaginatedResponse<GameSummary>>(
      '/games',
      queryParameters: const {'limit': 20, 'offset': 0},
      parse: (data) =>
          PaginatedResponse.fromJson(_asMap(data), GameSummary.fromJson),
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

  Future<NotificationItem> markNotificationRead(String notificationId) {
    return _apiClient.post<NotificationItem>(
      '/notifications/$notificationId/read',
      parse: (data) => NotificationItem.fromJson(_asMap(data)),
    );
  }

  Future<void> markAllNotificationsRead() {
    return _apiClient.post<void>('/notifications/read-all', parse: (_) {});
  }

  Future<int> fetchUnreadNotificationCount() {
    return _apiClient.get<int>(
      '/notifications/unread-count',
      parse: (data) => _asInt(_asMap(data)['unread_count']),
    );
  }

  Future<UserProfile> updateProfile({
    String? fullName,
    String? universityId,
    String? chesscomUsername,
  }) {
    final data = <String, Object?>{};
    if (fullName != null) {
      data['full_name'] = fullName;
    }
    if (universityId != null) {
      data['university_id'] = universityId;
    }
    if (chesscomUsername != null) {
      data['chesscom_username'] = chesscomUsername;
    }

    return _apiClient.patch<UserProfile>(
      '/users/me/profile',
      data: data,
      parse: (data) => UserProfile.fromJson(_asMap(data)),
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

  List<T> _list<T>(Object? value, T Function(Map<String, Object?> json) parse) {
    if (value is! List) {
      return const [];
    }
    return value
        .whereType<Map>()
        .map((item) => parse(Map<String, Object?>.from(item)))
        .toList();
  }
}
