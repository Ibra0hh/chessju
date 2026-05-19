import 'package:chessju_app/core/network/api_client.dart';
import 'package:chessju_app/core/network/api_providers.dart';
import 'package:chessju_app/core/pagination/pagination.dart';
import 'package:chessju_app/features/admin/data/admin_models.dart';
import 'package:chessju_app/shared/models/content_models.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final adminRepositoryProvider = Provider<AdminRepository>((ref) {
  return AdminRepository(ref.watch(apiClientProvider));
});

final adminIdentityProvider = FutureProvider.autoDispose<AdminIdentity>((ref) {
  return ref.watch(adminRepositoryProvider).fetchIdentity();
});

final adminNewsProvider =
    FutureProvider.autoDispose<PaginatedResponse<AdminArticle>>((ref) {
      return ref.watch(adminRepositoryProvider).listArticles();
    });

final adminAnnouncementsProvider =
    FutureProvider.autoDispose<PaginatedResponse<AdminAnnouncement>>((ref) {
      return ref.watch(adminRepositoryProvider).listAnnouncements();
    });

final adminTimeControlsProvider =
    FutureProvider.autoDispose<PaginatedResponse<AdminTimeControl>>((ref) {
      return ref.watch(adminRepositoryProvider).listTimeControls();
    });

final adminTournamentsProvider =
    FutureProvider.autoDispose<PaginatedResponse<AdminTournament>>((ref) {
      return ref.watch(adminRepositoryProvider).listTournaments();
    });

final adminTournamentDetailProvider = FutureProvider.autoDispose
    .family<AdminTournament, String>((ref, id) {
      return ref.watch(adminRepositoryProvider).getTournament(id);
    });

final adminTournamentRegistrationsProvider = FutureProvider.autoDispose
    .family<PaginatedResponse<AdminRegistration>, String>((ref, id) {
      return ref.watch(adminRepositoryProvider).listTournamentRegistrations(id);
    });

final adminRoundsProvider = FutureProvider.autoDispose
    .family<PaginatedResponse<AdminRound>, String>((ref, tournamentId) {
      return ref.watch(adminRepositoryProvider).listRounds(tournamentId);
    });

final adminPairingsProvider = FutureProvider.autoDispose
    .family<PaginatedResponse<AdminPairing>, String>((ref, roundId) {
      return ref.watch(adminRepositoryProvider).listPairings(roundId);
    });

final adminTournamentStandingsProvider = FutureProvider.autoDispose
    .family<List<StandingRow>, String>((ref, tournamentId) {
      return ref
          .watch(adminRepositoryProvider)
          .getTournamentStandings(tournamentId);
    });

final adminSeasonsProvider =
    FutureProvider.autoDispose<PaginatedResponse<SeasonSummary>>((ref) {
      return ref.watch(adminRepositoryProvider).listSeasons();
    });

final adminLeaderboardProvider = FutureProvider.autoDispose<LeaderboardContent>(
  (ref) {
    return ref.watch(adminRepositoryProvider).getLeaderboard();
  },
);

final adminAuditLogsProvider =
    FutureProvider.autoDispose<PaginatedResponse<AdminAuditLog>>((ref) {
      return ref.watch(adminRepositoryProvider).listAuditLogs();
    });

final adminGamesProvider =
    FutureProvider.autoDispose<PaginatedResponse<AdminRawItem>>((ref) {
      return ref.watch(adminRepositoryProvider).listRaw('/admin/games');
    });

final adminAnalysisJobsProvider =
    FutureProvider.autoDispose<PaginatedResponse<AdminRawItem>>((ref) {
      return ref.watch(adminRepositoryProvider).listRaw('/admin/analysis/jobs');
    });

final adminChessComSyncJobsProvider =
    FutureProvider.autoDispose<PaginatedResponse<AdminRawItem>>((ref) {
      return ref
          .watch(adminRepositoryProvider)
          .listRaw('/admin/chesscom/sync-jobs');
    });

final adminNotificationsProvider =
    FutureProvider.autoDispose<PaginatedResponse<AdminRawItem>>((ref) {
      return ref.watch(adminRepositoryProvider).listRaw('/admin/notifications');
    });

class AdminRepository {
  const AdminRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<AdminIdentity> fetchIdentity() {
    return _apiClient.get<AdminIdentity>(
      '/admin/me',
      parse: (data) => AdminIdentity.fromJson(_asMap(data)),
    );
  }

  Future<PaginatedResponse<AdminArticle>> listArticles() {
    return _list('/admin/news', AdminArticle.fromJson);
  }

  Future<AdminArticle> createArticle(Map<String, Object?> payload) {
    return _apiClient.post<AdminArticle>(
      '/admin/news',
      data: cleanPayload(payload),
      parse: (data) => AdminArticle.fromJson(_asMap(data)),
    );
  }

  Future<AdminArticle> updateArticle(String id, Map<String, Object?> payload) {
    return _apiClient.patch<AdminArticle>(
      '/admin/news/$id',
      data: cleanPayload(payload),
      parse: (data) => AdminArticle.fromJson(_asMap(data)),
    );
  }

  Future<AdminArticle> articleAction(String id, String action) {
    return _apiClient.post<AdminArticle>(
      '/admin/news/$id/$action',
      parse: (data) => AdminArticle.fromJson(_asMap(data)),
    );
  }

  Future<void> deleteArticle(String id) {
    return _apiClient.delete<void>('/admin/news/$id', parse: (_) {});
  }

  Future<PaginatedResponse<AdminAnnouncement>> listAnnouncements() {
    return _list('/admin/announcements', AdminAnnouncement.fromJson);
  }

  Future<AdminAnnouncement> createAnnouncement(Map<String, Object?> payload) {
    return _apiClient.post<AdminAnnouncement>(
      '/admin/announcements',
      data: cleanPayload(payload),
      parse: (data) => AdminAnnouncement.fromJson(_asMap(data)),
    );
  }

  Future<AdminAnnouncement> updateAnnouncement(
    String id,
    Map<String, Object?> payload,
  ) {
    return _apiClient.patch<AdminAnnouncement>(
      '/admin/announcements/$id',
      data: cleanPayload(payload),
      parse: (data) => AdminAnnouncement.fromJson(_asMap(data)),
    );
  }

  Future<AdminAnnouncement> announcementAction(String id, String action) {
    return _apiClient.post<AdminAnnouncement>(
      '/admin/announcements/$id/$action',
      parse: (data) => AdminAnnouncement.fromJson(_asMap(data)),
    );
  }

  Future<void> deleteAnnouncement(String id) {
    return _apiClient.delete<void>('/admin/announcements/$id', parse: (_) {});
  }

  Future<PaginatedResponse<AdminTimeControl>> listTimeControls() {
    return _list('/admin/time-controls', AdminTimeControl.fromJson, limit: 100);
  }

  Future<AdminTimeControl> createTimeControl(Map<String, Object?> payload) {
    return _apiClient.post<AdminTimeControl>(
      '/admin/time-controls',
      data: cleanPayload(payload),
      parse: (data) => AdminTimeControl.fromJson(_asMap(data)),
    );
  }

  Future<AdminTimeControl> updateTimeControl(
    String id,
    Map<String, Object?> payload,
  ) {
    return _apiClient.patch<AdminTimeControl>(
      '/admin/time-controls/$id',
      data: cleanPayload(payload),
      parse: (data) => AdminTimeControl.fromJson(_asMap(data)),
    );
  }

  Future<PaginatedResponse<AdminTournament>> listTournaments() {
    return _list(
      '/admin/tournaments',
      AdminTournament.fromJson,
      queryParameters: const {'include_deleted': true},
    );
  }

  Future<AdminTournament> getTournament(String id) {
    return _apiClient.get<AdminTournament>(
      '/admin/tournaments/$id',
      parse: (data) => AdminTournament.fromJson(_asMap(data)),
    );
  }

  Future<AdminTournament> createTournament(Map<String, Object?> payload) {
    return _apiClient.post<AdminTournament>(
      '/admin/tournaments',
      data: cleanPayload(payload),
      parse: (data) => AdminTournament.fromJson(_asMap(data)),
    );
  }

  Future<AdminTournament> updateTournament(
    String id,
    Map<String, Object?> payload,
  ) {
    return _apiClient.patch<AdminTournament>(
      '/admin/tournaments/$id',
      data: cleanPayload(payload),
      parse: (data) => AdminTournament.fromJson(_asMap(data)),
    );
  }

  Future<AdminTournament> tournamentAction(String id, String action) {
    return _apiClient.post<AdminTournament>(
      '/admin/tournaments/$id/$action',
      parse: (data) => AdminTournament.fromJson(_asMap(data)),
    );
  }

  Future<void> deleteTournament(String id) {
    return _apiClient.delete<void>('/admin/tournaments/$id', parse: (_) {});
  }

  Future<PaginatedResponse<AdminRegistration>> listTournamentRegistrations(
    String tournamentId,
  ) {
    return _list(
      '/admin/tournaments/$tournamentId/registrations',
      AdminRegistration.fromJson,
      limit: 100,
    );
  }

  Future<AdminRegistration> updateRegistration(
    String id,
    Map<String, Object?> payload,
  ) {
    return _apiClient.patch<AdminRegistration>(
      '/admin/tournament-registrations/$id',
      data: cleanPayload(payload),
      parse: (data) => AdminRegistration.fromJson(_asMap(data)),
    );
  }

  Future<PaginatedResponse<AdminRound>> listRounds(String tournamentId) {
    return _list(
      '/admin/tournaments/$tournamentId/rounds',
      AdminRound.fromJson,
      limit: 100,
    );
  }

  Future<AdminRound> createRound(
    String tournamentId,
    Map<String, Object?> payload,
  ) {
    return _apiClient.post<AdminRound>(
      '/admin/tournaments/$tournamentId/rounds',
      data: cleanPayload(payload),
      parse: (data) => AdminRound.fromJson(_asMap(data)),
    );
  }

  Future<AdminRound> updateRound(String id, Map<String, Object?> payload) {
    return _apiClient.patch<AdminRound>(
      '/admin/rounds/$id',
      data: cleanPayload(payload),
      parse: (data) => AdminRound.fromJson(_asMap(data)),
    );
  }

  Future<AdminRound> roundAction(String id, String action) {
    return _apiClient.post<AdminRound>(
      '/admin/rounds/$id/$action',
      parse: (data) => AdminRound.fromJson(_asMap(data)),
    );
  }

  Future<PaginatedResponse<AdminPairing>> listPairings(String roundId) {
    return _list(
      '/admin/rounds/$roundId/pairings',
      AdminPairing.fromJson,
      limit: 100,
    );
  }

  Future<AdminPairing> createPairing(
    String roundId,
    Map<String, Object?> payload,
  ) {
    return _apiClient.post<AdminPairing>(
      '/admin/rounds/$roundId/pairings',
      data: cleanPayload(payload),
      parse: (data) => AdminPairing.fromJson(_asMap(data)),
    );
  }

  Future<AdminPairing> updatePairing(String id, Map<String, Object?> payload) {
    return _apiClient.patch<AdminPairing>(
      '/admin/pairings/$id',
      data: cleanPayload(payload),
      parse: (data) => AdminPairing.fromJson(_asMap(data)),
    );
  }

  Future<AdminPairing> cancelPairing(String id) {
    return _apiClient.delete<AdminPairing>(
      '/admin/pairings/$id',
      parse: (data) => AdminPairing.fromJson(_asMap(data)),
    );
  }

  Future<AdminPairing> submitResult(String id, String result) {
    return _apiClient.post<AdminPairing>(
      '/admin/pairings/$id/result',
      data: {'result': result},
      parse: (data) => AdminPairing.fromJson(_asMap(data)),
    );
  }

  Future<List<StandingRow>> getTournamentStandings(String tournamentId) {
    return _apiClient.get<List<StandingRow>>(
      '/admin/tournaments/$tournamentId/standings',
      parse: (data) => _listItems(_asMap(data)['items'], StandingRow.fromJson),
    );
  }

  Future<PaginatedResponse<SeasonSummary>> listSeasons() {
    return _list('/admin/leaderboard/seasons', SeasonSummary.fromJson);
  }

  Future<SeasonSummary> createSeason(Map<String, Object?> payload) {
    return _apiClient.post<SeasonSummary>(
      '/admin/leaderboard/seasons',
      data: cleanPayload(payload),
      parse: (data) => SeasonSummary.fromJson(_asMap(data)),
    );
  }

  Future<SeasonSummary> activateSeason(String id) {
    return _apiClient.post<SeasonSummary>(
      '/admin/leaderboard/seasons/$id/activate',
      parse: (data) => SeasonSummary.fromJson(_asMap(data)),
    );
  }

  Future<LeaderboardContent> recomputeLeaderboard({String? seasonId}) {
    return _apiClient.post<LeaderboardContent>(
      '/admin/leaderboard/recompute',
      data: seasonId == null || seasonId.isEmpty
          ? const {}
          : {'season_id': seasonId},
      parse: (data) => LeaderboardContent.fromJson(_asMap(data)),
    );
  }

  Future<LeaderboardContent> getLeaderboard() {
    return _apiClient.get<LeaderboardContent>(
      '/admin/leaderboard',
      parse: (data) => LeaderboardContent.fromJson(_asMap(data)),
    );
  }

  Future<PaginatedResponse<AdminAuditLog>> listAuditLogs() {
    return _list('/admin/audit-logs', AdminAuditLog.fromJson);
  }

  Future<PaginatedResponse<AdminRawItem>> listRaw(String path) {
    return _list(path, AdminRawItem.fromJson);
  }

  Future<PaginatedResponse<T>> _list<T>(
    String path,
    T Function(Map<String, Object?> item) parseItem, {
    int limit = 50,
    Map<String, Object?> queryParameters = const {},
  }) {
    return _apiClient.get<PaginatedResponse<T>>(
      path,
      queryParameters: {'limit': limit, 'offset': 0, ...queryParameters},
      parse: (data) => PaginatedResponse.fromJson(_asMap(data), parseItem),
    );
  }

  Map<String, Object?> _asMap(Object? data) {
    return Map<String, Object?>.from(data as Map? ?? const {});
  }

  List<T> _listItems<T>(
    Object? value,
    T Function(Map<String, Object?> item) parseItem,
  ) {
    if (value is! List) {
      return const [];
    }
    return value
        .whereType<Map>()
        .map((item) => parseItem(Map<String, Object?>.from(item)))
        .toList();
  }
}
