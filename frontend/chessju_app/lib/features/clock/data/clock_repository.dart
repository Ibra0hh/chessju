import 'package:chessju_app/core/network/api_client.dart';
import 'package:chessju_app/core/network/api_providers.dart';
import 'package:chessju_app/core/pagination/pagination.dart';
import 'package:chessju_app/features/clock/data/clock_models.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final clockRepositoryProvider = Provider<ClockRepository>((ref) {
  return ClockRepository(ref.watch(apiClientProvider));
});

class ClockRepository {
  const ClockRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<ClockSession> createSession({
    required int baseSeconds,
    required int incrementSeconds,
    int delaySeconds = 0,
  }) {
    return _apiClient.post<ClockSession>(
      '/clock/sessions',
      data: {
        'base_seconds': baseSeconds,
        'increment_seconds': incrementSeconds,
        'delay_seconds': delaySeconds,
      },
      parse: (data) => ClockSession.fromJson(_asMap(data)),
    );
  }

  Future<ClockSession> getSession(String sessionId) {
    return _apiClient.get<ClockSession>(
      '/clock/sessions/$sessionId',
      parse: (data) => ClockSession.fromJson(_asMap(data)),
    );
  }

  Future<PaginatedResponse<ClockEvent>> getEvents(String sessionId) {
    return _apiClient.get<PaginatedResponse<ClockEvent>>(
      '/clock/sessions/$sessionId/events',
      queryParameters: const {'limit': 100, 'offset': 0},
      parse: (data) =>
          PaginatedResponse.fromJson(_asMap(data), ClockEvent.fromJson),
    );
  }

  Future<ClockSession> start({
    required ClockSession session,
    required int whiteRemainingMs,
    required int blackRemainingMs,
    String activeColor = 'white',
  }) {
    return _mutate(
      session.id,
      'start',
      _snapshot(
        whiteRemainingMs,
        blackRemainingMs,
        extra: {'active_color': activeColor},
      ),
    );
  }

  Future<ClockSession> pause({
    required ClockSession session,
    required int whiteRemainingMs,
    required int blackRemainingMs,
  }) {
    return _mutate(
      session.id,
      'pause',
      _snapshot(whiteRemainingMs, blackRemainingMs),
    );
  }

  Future<ClockSession> resume({
    required ClockSession session,
    required int whiteRemainingMs,
    required int blackRemainingMs,
    required String activeColor,
  }) {
    return _mutate(
      session.id,
      'resume',
      _snapshot(
        whiteRemainingMs,
        blackRemainingMs,
        extra: {'active_color': activeColor},
      ),
    );
  }

  Future<ClockSession> switchTurn({
    required ClockSession session,
    required int whiteRemainingMs,
    required int blackRemainingMs,
    required String activeColor,
  }) {
    return _mutate(
      session.id,
      'switch-turn',
      _snapshot(
        whiteRemainingMs,
        blackRemainingMs,
        extra: {'active_color': activeColor},
      ),
    );
  }

  Future<ClockSession> adjust({
    required ClockSession session,
    required int whiteRemainingMs,
    required int blackRemainingMs,
    String? reason,
  }) {
    final extra = <String, Object?>{};
    if (reason != null) {
      extra['reason'] = reason;
    }

    return _mutate(
      session.id,
      'adjust',
      _snapshot(whiteRemainingMs, blackRemainingMs, extra: extra),
    );
  }

  Future<ClockSession> flag({
    required ClockSession session,
    required int whiteRemainingMs,
    required int blackRemainingMs,
    required String flaggedColor,
  }) {
    return _mutate(
      session.id,
      'flag',
      _snapshot(
        whiteRemainingMs,
        blackRemainingMs,
        extra: {'flagged_color': flaggedColor},
      ),
    );
  }

  Future<ClockSession> complete({
    required ClockSession session,
    required int whiteRemainingMs,
    required int blackRemainingMs,
    String result = 'manual',
  }) {
    return _mutate(
      session.id,
      'complete',
      _snapshot(whiteRemainingMs, blackRemainingMs, extra: {'result': result}),
    );
  }

  Future<ClockSession> reset(ClockSession session) {
    return _mutate(session.id, 'reset', _timestampOnly());
  }

  Future<ClockSession> cancel({
    required ClockSession session,
    required int whiteRemainingMs,
    required int blackRemainingMs,
    String? reason,
  }) {
    final extra = <String, Object?>{};
    if (reason != null) {
      extra['reason'] = reason;
    }

    return _mutate(
      session.id,
      'cancel',
      _snapshot(whiteRemainingMs, blackRemainingMs, extra: extra),
    );
  }

  Future<ClockSession> _mutate(
    String sessionId,
    String action,
    Map<String, Object?> data,
  ) {
    return _apiClient.post<ClockSession>(
      '/clock/sessions/$sessionId/$action',
      data: data,
      parse: (data) => ClockSession.fromJson(_asMap(data)),
    );
  }

  Map<String, Object?> _snapshot(
    int whiteRemainingMs,
    int blackRemainingMs, {
    Map<String, Object?> extra = const {},
  }) {
    return {
      'white_remaining_ms': whiteRemainingMs < 0 ? 0 : whiteRemainingMs,
      'black_remaining_ms': blackRemainingMs < 0 ? 0 : blackRemainingMs,
      'client_timestamp': DateTime.now().toUtc().toIso8601String(),
      ...extra,
    };
  }

  Map<String, Object?> _timestampOnly() {
    return {'client_timestamp': DateTime.now().toUtc().toIso8601String()};
  }

  Map<String, Object?> _asMap(Object? data) {
    return Map<String, Object?>.from(data as Map? ?? const {});
  }
}
