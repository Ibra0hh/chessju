import 'package:chessju_app/core/network/api_client.dart';
import 'package:chessju_app/core/network/api_providers.dart';
import 'package:chessju_app/core/pagination/pagination.dart';
import 'package:chessju_app/features/games/data/game_models.dart';
import 'package:chessju_app/shared/models/content_models.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final gamesRepositoryProvider = Provider<GamesRepository>((ref) {
  return GamesRepository(ref.watch(apiClientProvider));
});

final gameListProvider = FutureProvider.autoDispose
    .family<PaginatedResponse<GameSummary>, String?>((ref, source) {
      return ref.watch(gamesRepositoryProvider).fetchGames(source: source);
    });

final gameDetailProvider = FutureProvider.autoDispose
    .family<GameDetail, String>((ref, gameId) {
      return ref.watch(gamesRepositoryProvider).fetchGameDetail(gameId);
    });

final gameAnalysisProvider = FutureProvider.autoDispose
    .family<GameAnalysisState, String>((ref, gameId) {
      return ref.watch(gamesRepositoryProvider).fetchGameAnalysis(gameId);
    });

final analysisJobProvider = FutureProvider.autoDispose
    .family<AnalysisJob, String>((ref, jobId) {
      return ref.watch(gamesRepositoryProvider).fetchAnalysisJob(jobId);
    });

class GamesRepository {
  const GamesRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<PaginatedResponse<GameSummary>> fetchGames({
    String? source,
    int limit = 50,
    int offset = 0,
  }) {
    final query = <String, Object?>{'limit': limit, 'offset': offset};
    if (source != null && source.isNotEmpty) {
      query['source'] = source;
    }

    return _apiClient.get<PaginatedResponse<GameSummary>>(
      '/games',
      queryParameters: query,
      parse: (data) =>
          PaginatedResponse.fromJson(_asMap(data), GameSummary.fromJson),
    );
  }

  Future<GameDetail> fetchGameDetail(String gameId) {
    return _apiClient.get<GameDetail>(
      '/games/$gameId',
      parse: (data) => GameDetail.fromJson(_asMap(data)),
    );
  }

  Future<GameDetail> pastePgn(String pgnText) {
    return _apiClient.post<GameDetail>(
      '/games/pgn/paste',
      data: {'pgn_text': pgnText},
      parse: (data) => GameDetail.fromJson(_asMap(data)),
    );
  }

  Future<AnalysisJob> requestAnalysis(String gameId, {int? depth}) {
    final data = <String, Object?>{};
    if (depth != null) {
      data['depth'] = depth;
    }

    return _apiClient.post<AnalysisJob>(
      '/games/$gameId/analysis',
      data: data,
      parse: (data) => AnalysisJob.fromJson(_asMap(data)),
    );
  }

  Future<GameAnalysisState> fetchGameAnalysis(String gameId) {
    return _apiClient.get<GameAnalysisState>(
      '/games/$gameId/analysis',
      parse: (data) => GameAnalysisState.fromJson(_asMap(data)),
    );
  }

  Future<AnalysisJob> fetchAnalysisJob(String jobId) {
    return _apiClient.get<AnalysisJob>(
      '/analysis/jobs/$jobId',
      parse: (data) => AnalysisJob.fromJson(_asMap(data)),
    );
  }

  Future<AnalysisReport> fetchAnalysisReport(String reportId) {
    return _apiClient.get<AnalysisReport>(
      '/analysis/reports/$reportId',
      parse: (data) => AnalysisReport.fromJson(_asMap(data)),
    );
  }

  Map<String, Object?> _asMap(Object? data) {
    return Map<String, Object?>.from(data as Map? ?? const {});
  }
}
