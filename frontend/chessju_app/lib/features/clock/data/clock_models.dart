class ClockSession {
  const ClockSession({
    required this.id,
    this.tournamentId,
    this.pairingId,
    this.whiteUserId,
    this.blackUserId,
    required this.baseSeconds,
    required this.incrementSeconds,
    required this.delaySeconds,
    required this.whiteRemainingMs,
    required this.blackRemainingMs,
    required this.activeColor,
    required this.status,
    this.result,
    required this.createdBy,
    this.lastEventAt,
    this.startedAt,
    this.completedAt,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String? tournamentId;
  final String? pairingId;
  final String? whiteUserId;
  final String? blackUserId;
  final int baseSeconds;
  final int incrementSeconds;
  final int delaySeconds;
  final int whiteRemainingMs;
  final int blackRemainingMs;
  final String activeColor;
  final String status;
  final String? result;
  final String createdBy;
  final String? lastEventAt;
  final String? startedAt;
  final String? completedAt;
  final String createdAt;
  final String updatedAt;

  bool get isRunning => status == 'running';
  bool get isPaused => status == 'paused';
  bool get isSetup => status == 'setup';
  bool get isEnded => status == 'completed' || status == 'cancelled';

  ClockSession copyWith({
    int? whiteRemainingMs,
    int? blackRemainingMs,
    String? activeColor,
    String? status,
    String? result,
  }) {
    return ClockSession(
      id: id,
      tournamentId: tournamentId,
      pairingId: pairingId,
      whiteUserId: whiteUserId,
      blackUserId: blackUserId,
      baseSeconds: baseSeconds,
      incrementSeconds: incrementSeconds,
      delaySeconds: delaySeconds,
      whiteRemainingMs: whiteRemainingMs ?? this.whiteRemainingMs,
      blackRemainingMs: blackRemainingMs ?? this.blackRemainingMs,
      activeColor: activeColor ?? this.activeColor,
      status: status ?? this.status,
      result: result ?? this.result,
      createdBy: createdBy,
      lastEventAt: lastEventAt,
      startedAt: startedAt,
      completedAt: completedAt,
      createdAt: createdAt,
      updatedAt: updatedAt,
    );
  }

  factory ClockSession.fromJson(Map<String, Object?> json) {
    return ClockSession(
      id: json['id']?.toString() ?? '',
      tournamentId: json['tournament_id']?.toString(),
      pairingId: json['pairing_id']?.toString(),
      whiteUserId: json['white_user_id']?.toString(),
      blackUserId: json['black_user_id']?.toString(),
      baseSeconds: _asInt(json['base_seconds']),
      incrementSeconds: _asInt(json['increment_seconds']),
      delaySeconds: _asInt(json['delay_seconds']),
      whiteRemainingMs: _asInt(json['white_remaining_ms']),
      blackRemainingMs: _asInt(json['black_remaining_ms']),
      activeColor: json['active_color']?.toString() ?? 'none',
      status: json['status']?.toString() ?? 'setup',
      result: json['result']?.toString(),
      createdBy: json['created_by']?.toString() ?? '',
      lastEventAt: json['last_event_at']?.toString(),
      startedAt: json['started_at']?.toString(),
      completedAt: json['completed_at']?.toString(),
      createdAt: json['created_at']?.toString() ?? '',
      updatedAt: json['updated_at']?.toString() ?? '',
    );
  }
}

class ClockEvent {
  const ClockEvent({
    required this.id,
    required this.clockSessionId,
    required this.eventType,
    this.actorUserId,
    required this.whiteRemainingMs,
    required this.blackRemainingMs,
    required this.activeColor,
    this.clientTimestamp,
    required this.serverTimestamp,
    this.metadata = const {},
  });

  final String id;
  final String clockSessionId;
  final String eventType;
  final String? actorUserId;
  final int whiteRemainingMs;
  final int blackRemainingMs;
  final String activeColor;
  final String? clientTimestamp;
  final String serverTimestamp;
  final Map<String, Object?> metadata;

  factory ClockEvent.fromJson(Map<String, Object?> json) {
    return ClockEvent(
      id: json['id']?.toString() ?? '',
      clockSessionId: json['clock_session_id']?.toString() ?? '',
      eventType: json['event_type']?.toString() ?? '',
      actorUserId: json['actor_user_id']?.toString(),
      whiteRemainingMs: _asInt(json['white_remaining_ms']),
      blackRemainingMs: _asInt(json['black_remaining_ms']),
      activeColor: json['active_color']?.toString() ?? 'none',
      clientTimestamp: json['client_timestamp']?.toString(),
      serverTimestamp: json['server_timestamp']?.toString() ?? '',
      metadata: json['metadata'] is Map
          ? Map<String, Object?>.from(json['metadata'] as Map)
          : const {},
    );
  }
}

class ClockPreset {
  const ClockPreset(this.label, this.baseSeconds, this.incrementSeconds);

  final String label;
  final int baseSeconds;
  final int incrementSeconds;
}

const clockPresets = [
  ClockPreset('1 + 0', 60, 0),
  ClockPreset('1 + 1', 60, 1),
  ClockPreset('3 + 0', 180, 0),
  ClockPreset('3 + 2', 180, 2),
  ClockPreset('5 + 0', 300, 0),
  ClockPreset('5 + 3', 300, 3),
  ClockPreset('10 + 0', 600, 0),
  ClockPreset('15 + 10', 900, 10),
];

String formatClockTime(int milliseconds) {
  final clamped = milliseconds < 0 ? 0 : milliseconds;
  final totalSeconds = (clamped / 1000).ceil();
  final minutes = totalSeconds ~/ 60;
  final seconds = totalSeconds % 60;
  return '$minutes:${seconds.toString().padLeft(2, '0')}';
}

String? validateBaseSeconds(int baseSeconds) {
  if (baseSeconds <= 0) {
    return 'Base time must be greater than zero.';
  }
  return null;
}

String? validateIncrementSeconds(int incrementSeconds) {
  if (incrementSeconds < 0) {
    return 'Increment cannot be negative.';
  }
  return null;
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
