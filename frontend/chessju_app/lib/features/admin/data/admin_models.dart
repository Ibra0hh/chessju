import 'package:chessju_app/features/auth/data/auth_models.dart';

const adminRoles = {'admin', 'super_admin'};

bool hasAdminAccessForRoles(Iterable<String> roles) {
  return roles.any(adminRoles.contains);
}

String? validateRequiredText(String? value, String label) {
  if ((value ?? '').trim().isEmpty) {
    return '$label is required';
  }
  return null;
}

String? validatePositiveIntegerText(String? value, String label) {
  final number = int.tryParse((value ?? '').trim());
  if (number == null || number <= 0) {
    return '$label must be greater than 0';
  }
  return null;
}

String resultLabelFor(String value) {
  return switch (value) {
    'pending' => 'Pending',
    'white_win' => 'White win',
    'black_win' => 'Black win',
    'draw' => 'Draw',
    'white_forfeit' => 'White forfeit',
    'black_forfeit' => 'Black forfeit',
    'double_forfeit' => 'Double forfeit',
    'bye' => 'Bye',
    _ => value.replaceAll('_', ' '),
  };
}

extension CurrentUserAdminAccess on CurrentUser {
  bool get isAdmin => hasAdminAccessForRoles(roles);
}

class AdminIdentity {
  const AdminIdentity({
    required this.id,
    required this.email,
    required this.roles,
    required this.username,
    required this.fullName,
  });

  final String id;
  final String email;
  final List<String> roles;
  final String username;
  final String fullName;

  bool get isAdmin => hasAdminAccessForRoles(roles);

  factory AdminIdentity.fromJson(Map<String, Object?> json) {
    return AdminIdentity(
      id: json['id']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      roles: _stringList(json['roles']),
      username: json['username']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
    );
  }
}

class AdminArticle {
  const AdminArticle({
    required this.id,
    required this.title,
    required this.slug,
    this.summary,
    this.coverFileId,
    required this.status,
    this.publishedAt,
    required this.createdAt,
    required this.updatedAt,
    this.authorId,
    this.bodyMarkdown = '',
    this.deletedAt,
  });

  final String id;
  final String title;
  final String slug;
  final String? summary;
  final String? coverFileId;
  final String status;
  final String? publishedAt;
  final String createdAt;
  final String updatedAt;
  final String? authorId;
  final String bodyMarkdown;
  final String? deletedAt;

  factory AdminArticle.fromJson(Map<String, Object?> json) {
    return AdminArticle(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      slug: json['slug']?.toString() ?? '',
      summary: json['summary']?.toString(),
      coverFileId: json['cover_file_id']?.toString(),
      status: json['status']?.toString() ?? '',
      publishedAt: json['published_at']?.toString(),
      createdAt: json['created_at']?.toString() ?? '',
      updatedAt: json['updated_at']?.toString() ?? '',
      authorId: json['author_id']?.toString(),
      bodyMarkdown: json['body_markdown']?.toString() ?? '',
      deletedAt: json['deleted_at']?.toString(),
    );
  }
}

class AdminAnnouncement {
  const AdminAnnouncement({
    required this.id,
    required this.createdBy,
    required this.title,
    required this.message,
    required this.target,
    required this.priority,
    required this.status,
    this.publishedAt,
    this.expiresAt,
    this.tournamentId,
    required this.createdAt,
    required this.updatedAt,
    this.deletedAt,
  });

  final String id;
  final String createdBy;
  final String title;
  final String message;
  final String target;
  final String priority;
  final String status;
  final String? publishedAt;
  final String? expiresAt;
  final String? tournamentId;
  final String createdAt;
  final String updatedAt;
  final String? deletedAt;

  factory AdminAnnouncement.fromJson(Map<String, Object?> json) {
    return AdminAnnouncement(
      id: json['id']?.toString() ?? '',
      createdBy: json['created_by']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      message: json['message']?.toString() ?? '',
      target: json['target']?.toString() ?? 'all',
      priority: json['priority']?.toString() ?? 'normal',
      status: json['status']?.toString() ?? '',
      publishedAt: json['published_at']?.toString(),
      expiresAt: json['expires_at']?.toString(),
      tournamentId: json['tournament_id']?.toString(),
      createdAt: json['created_at']?.toString() ?? '',
      updatedAt: json['updated_at']?.toString() ?? '',
      deletedAt: json['deleted_at']?.toString(),
    );
  }
}

class AdminTimeControl {
  const AdminTimeControl({
    required this.id,
    required this.name,
    required this.baseSeconds,
    required this.incrementSeconds,
    required this.delaySeconds,
    required this.type,
    this.createdAt,
    this.updatedAt,
  });

  final String id;
  final String name;
  final int baseSeconds;
  final int incrementSeconds;
  final int delaySeconds;
  final String type;
  final String? createdAt;
  final String? updatedAt;

  factory AdminTimeControl.fromJson(Map<String, Object?> json) {
    return AdminTimeControl(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      baseSeconds: _asInt(json['base_seconds']),
      incrementSeconds: _asInt(json['increment_seconds']),
      delaySeconds: _asInt(json['delay_seconds']),
      type: json['type']?.toString() ?? '',
      createdAt: json['created_at']?.toString(),
      updatedAt: json['updated_at']?.toString(),
    );
  }
}

class AdminTournament {
  const AdminTournament({
    required this.id,
    required this.title,
    required this.slug,
    required this.status,
    required this.format,
    required this.startsAt,
    this.location,
    this.coverFileId,
    this.timeControl,
    this.maxPlayers,
    this.approvedCount = 0,
    this.waitlistedCount = 0,
    this.spotsRemaining,
    this.description,
    this.endsAt,
    this.registrationOpenAt,
    this.registrationCloseAt,
    this.createdAt,
    this.createdBy,
    this.updatedAt,
    this.deletedAt,
  });

  final String id;
  final String title;
  final String slug;
  final String status;
  final String format;
  final String startsAt;
  final String? location;
  final String? coverFileId;
  final AdminTimeControl? timeControl;
  final int? maxPlayers;
  final int approvedCount;
  final int waitlistedCount;
  final int? spotsRemaining;
  final String? description;
  final String? endsAt;
  final String? registrationOpenAt;
  final String? registrationCloseAt;
  final String? createdAt;
  final String? createdBy;
  final String? updatedAt;
  final String? deletedAt;

  factory AdminTournament.fromJson(Map<String, Object?> json) {
    return AdminTournament(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      slug: json['slug']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      format: json['format']?.toString() ?? '',
      startsAt: json['starts_at']?.toString() ?? '',
      location: json['location']?.toString(),
      coverFileId: json['cover_file_id']?.toString(),
      timeControl: json['time_control'] is Map
          ? AdminTimeControl.fromJson(_asMap(json['time_control']))
          : null,
      maxPlayers: _nullableInt(json['max_players']),
      approvedCount: _asInt(json['approved_count']),
      waitlistedCount: _asInt(json['waitlisted_count']),
      spotsRemaining: _nullableInt(json['spots_remaining']),
      description: json['description']?.toString(),
      endsAt: json['ends_at']?.toString(),
      registrationOpenAt: json['registration_open_at']?.toString(),
      registrationCloseAt: json['registration_close_at']?.toString(),
      createdAt: json['created_at']?.toString(),
      createdBy: json['created_by']?.toString(),
      updatedAt: json['updated_at']?.toString(),
      deletedAt: json['deleted_at']?.toString(),
    );
  }
}

class AdminRegistration {
  const AdminRegistration({
    required this.id,
    required this.tournamentId,
    required this.userId,
    required this.status,
    this.seedRating,
    this.checkedInAt,
    required this.createdAt,
    required this.updatedAt,
    this.cancelledAt,
  });

  final String id;
  final String tournamentId;
  final String userId;
  final String status;
  final int? seedRating;
  final String? checkedInAt;
  final String createdAt;
  final String updatedAt;
  final String? cancelledAt;

  factory AdminRegistration.fromJson(Map<String, Object?> json) {
    return AdminRegistration(
      id: json['id']?.toString() ?? '',
      tournamentId: json['tournament_id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      seedRating: _nullableInt(json['seed_rating']),
      checkedInAt: json['checked_in_at']?.toString(),
      createdAt: json['created_at']?.toString() ?? '',
      updatedAt: json['updated_at']?.toString() ?? '',
      cancelledAt: json['cancelled_at']?.toString(),
    );
  }
}

class AdminPlayerSummary {
  const AdminPlayerSummary({
    required this.id,
    required this.username,
    required this.fullName,
  });

  final String id;
  final String username;
  final String fullName;

  String get displayName => fullName.isNotEmpty ? fullName : username;

  factory AdminPlayerSummary.fromJson(Map<String, Object?> json) {
    return AdminPlayerSummary(
      id: json['id']?.toString() ?? '',
      username: json['username']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
    );
  }
}

class AdminRound {
  const AdminRound({
    required this.id,
    required this.tournamentId,
    required this.roundNumber,
    this.title,
    required this.status,
    this.startsAt,
    this.createdAt,
    this.updatedAt,
    this.pairings = const [],
  });

  final String id;
  final String tournamentId;
  final int roundNumber;
  final String? title;
  final String status;
  final String? startsAt;
  final String? createdAt;
  final String? updatedAt;
  final List<AdminPairing> pairings;

  factory AdminRound.fromJson(Map<String, Object?> json) {
    return AdminRound(
      id: json['id']?.toString() ?? '',
      tournamentId: json['tournament_id']?.toString() ?? '',
      roundNumber: _asInt(json['round_number']),
      title: json['title']?.toString(),
      status: json['status']?.toString() ?? '',
      startsAt: json['starts_at']?.toString(),
      createdAt: json['created_at']?.toString(),
      updatedAt: json['updated_at']?.toString(),
      pairings: _list(json['pairings'], AdminPairing.fromJson),
    );
  }
}

class AdminPairing {
  const AdminPairing({
    required this.id,
    required this.roundId,
    required this.tournamentId,
    required this.boardNumber,
    this.whiteUser,
    this.blackUser,
    required this.status,
    required this.result,
    this.resultReportedAt,
    this.createdAt,
    this.updatedAt,
  });

  final String id;
  final String roundId;
  final String tournamentId;
  final int boardNumber;
  final AdminPlayerSummary? whiteUser;
  final AdminPlayerSummary? blackUser;
  final String status;
  final String result;
  final String? resultReportedAt;
  final String? createdAt;
  final String? updatedAt;

  factory AdminPairing.fromJson(Map<String, Object?> json) {
    return AdminPairing(
      id: json['id']?.toString() ?? '',
      roundId: json['round_id']?.toString() ?? '',
      tournamentId: json['tournament_id']?.toString() ?? '',
      boardNumber: _asInt(json['board_number']),
      whiteUser: json['white_user'] is Map
          ? AdminPlayerSummary.fromJson(_asMap(json['white_user']))
          : null,
      blackUser: json['black_user'] is Map
          ? AdminPlayerSummary.fromJson(_asMap(json['black_user']))
          : null,
      status: json['status']?.toString() ?? '',
      result: json['result']?.toString() ?? '',
      resultReportedAt: json['result_reported_at']?.toString(),
      createdAt: json['created_at']?.toString(),
      updatedAt: json['updated_at']?.toString(),
    );
  }
}

class AdminAuditLog {
  const AdminAuditLog({
    required this.id,
    required this.adminId,
    required this.action,
    required this.entityType,
    this.entityId,
    this.before,
    this.after,
    this.ipAddress,
    this.userAgent,
    required this.createdAt,
  });

  final String id;
  final String adminId;
  final String action;
  final String entityType;
  final String? entityId;
  final Map<String, Object?>? before;
  final Map<String, Object?>? after;
  final String? ipAddress;
  final String? userAgent;
  final String createdAt;

  factory AdminAuditLog.fromJson(Map<String, Object?> json) {
    return AdminAuditLog(
      id: json['id']?.toString() ?? '',
      adminId: json['admin_id']?.toString() ?? '',
      action: json['action']?.toString() ?? '',
      entityType: json['entity_type']?.toString() ?? '',
      entityId: json['entity_id']?.toString(),
      before: json['before'] is Map ? _asMap(json['before']) : null,
      after: json['after'] is Map ? _asMap(json['after']) : null,
      ipAddress: json['ip_address']?.toString(),
      userAgent: json['user_agent']?.toString(),
      createdAt: json['created_at']?.toString() ?? '',
    );
  }
}

class AdminRawItem {
  const AdminRawItem({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.createdAt,
  });

  final String id;
  final String title;
  final String subtitle;
  final String createdAt;

  factory AdminRawItem.fromJson(Map<String, Object?> json) {
    final id =
        json['id']?.toString() ??
        json['game_id']?.toString() ??
        json['analysis_job_id']?.toString() ??
        '';
    final title =
        json['title']?.toString() ??
        json['status']?.toString() ??
        json['source']?.toString() ??
        json['type']?.toString() ??
        id;
    final subtitle = [
      if (json['user_id'] != null) 'user ${json['user_id']}',
      if (json['game_id'] != null) 'game ${json['game_id']}',
      if (json['requested_by'] != null) 'requested by ${json['requested_by']}',
      if (json['chesscom_url'] != null) json['chesscom_url'],
      if (json['created_at'] != null) json['created_at'],
    ].join(' | ');

    return AdminRawItem(
      id: id,
      title: title,
      subtitle: subtitle,
      createdAt: json['created_at']?.toString() ?? '',
    );
  }
}

Map<String, Object?> cleanPayload(Map<String, Object?> input) {
  final output = <String, Object?>{};
  for (final entry in input.entries) {
    final value = entry.value;
    if (value == null) {
      continue;
    }
    if (value is String && value.trim().isEmpty) {
      continue;
    }
    output[entry.key] = value is String ? value.trim() : value;
  }
  return output;
}

Map<String, Object?> _asMap(Object? value) {
  return Map<String, Object?>.from(value as Map? ?? const {});
}

List<String> _stringList(Object? value) {
  if (value is! List) {
    return const [];
  }
  return value.map((item) => item.toString()).toList();
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

int _asInt(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

int? _nullableInt(Object? value) {
  if (value == null) {
    return null;
  }
  return _asInt(value);
}
