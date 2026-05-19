class ArticleSummary {
  const ArticleSummary({
    required this.id,
    required this.title,
    required this.slug,
    this.summary,
    this.publishedAt,
  });

  final String id;
  final String title;
  final String slug;
  final String? summary;
  final String? publishedAt;

  factory ArticleSummary.fromJson(Map<String, Object?> json) {
    return ArticleSummary(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      slug: json['slug']?.toString() ?? '',
      summary: json['summary']?.toString(),
      publishedAt: json['published_at']?.toString(),
    );
  }
}

class ArticleDetail extends ArticleSummary {
  const ArticleDetail({
    required super.id,
    required super.title,
    required super.slug,
    super.summary,
    super.publishedAt,
    required this.bodyMarkdown,
    this.authorId,
  });

  final String bodyMarkdown;
  final String? authorId;

  factory ArticleDetail.fromJson(Map<String, Object?> json) {
    return ArticleDetail(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      slug: json['slug']?.toString() ?? '',
      summary: json['summary']?.toString(),
      publishedAt: json['published_at']?.toString(),
      bodyMarkdown: json['body_markdown']?.toString() ?? '',
      authorId: json['author_id']?.toString(),
    );
  }
}

class AnnouncementSummary {
  const AnnouncementSummary({
    required this.id,
    required this.title,
    required this.message,
    required this.priority,
    this.expiresAt,
  });

  final String id;
  final String title;
  final String message;
  final String priority;
  final String? expiresAt;

  factory AnnouncementSummary.fromJson(Map<String, Object?> json) {
    return AnnouncementSummary(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      message: json['message']?.toString() ?? '',
      priority: json['priority']?.toString() ?? 'normal',
      expiresAt: json['expires_at']?.toString(),
    );
  }
}

class TournamentSummary {
  const TournamentSummary({
    required this.id,
    required this.title,
    required this.slug,
    required this.status,
    required this.format,
    required this.startsAt,
    this.location,
    this.maxPlayers,
    this.approvedCount = 0,
    this.waitlistedCount = 0,
    this.spotsRemaining,
    this.timeControl,
  });

  final String id;
  final String title;
  final String slug;
  final String status;
  final String format;
  final String startsAt;
  final String? location;
  final int? maxPlayers;
  final int approvedCount;
  final int waitlistedCount;
  final int? spotsRemaining;
  final TimeControlSummary? timeControl;

  factory TournamentSummary.fromJson(Map<String, Object?> json) {
    return TournamentSummary(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      slug: json['slug']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      format: json['format']?.toString() ?? '',
      startsAt: json['starts_at']?.toString() ?? '',
      location: json['location']?.toString(),
      maxPlayers: _nullableInt(json['max_players']),
      approvedCount: _asInt(json['approved_count']),
      waitlistedCount: _asInt(json['waitlisted_count']),
      spotsRemaining: _nullableInt(json['spots_remaining']),
      timeControl: json['time_control'] is Map
          ? TimeControlSummary.fromJson(
              Map<String, Object?>.from(json['time_control'] as Map),
            )
          : null,
    );
  }
}

class TimeControlSummary {
  const TimeControlSummary({
    required this.id,
    required this.name,
    required this.baseSeconds,
    required this.incrementSeconds,
    required this.delaySeconds,
    required this.type,
  });

  final String id;
  final String name;
  final int baseSeconds;
  final int incrementSeconds;
  final int delaySeconds;
  final String type;

  factory TimeControlSummary.fromJson(Map<String, Object?> json) {
    return TimeControlSummary(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      baseSeconds: _asInt(json['base_seconds']),
      incrementSeconds: _asInt(json['increment_seconds']),
      delaySeconds: _asInt(json['delay_seconds']),
      type: json['type']?.toString() ?? '',
    );
  }
}

class TournamentRegistration {
  const TournamentRegistration({
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

  factory TournamentRegistration.fromJson(Map<String, Object?> json) {
    return TournamentRegistration(
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

class TournamentDetail extends TournamentSummary {
  const TournamentDetail({
    required super.id,
    required super.title,
    required super.slug,
    required super.status,
    required super.format,
    required super.startsAt,
    super.location,
    super.maxPlayers,
    super.approvedCount,
    super.waitlistedCount,
    super.spotsRemaining,
    super.timeControl,
    this.description,
    this.endsAt,
    this.registrationOpenAt,
    this.registrationCloseAt,
    this.createdAt,
    this.myRegistration,
  });

  final String? description;
  final String? endsAt;
  final String? registrationOpenAt;
  final String? registrationCloseAt;
  final String? createdAt;
  final TournamentRegistration? myRegistration;

  factory TournamentDetail.fromJson(Map<String, Object?> json) {
    final summary = TournamentSummary.fromJson(json);
    return TournamentDetail(
      id: summary.id,
      title: summary.title,
      slug: summary.slug,
      status: summary.status,
      format: summary.format,
      startsAt: summary.startsAt,
      location: summary.location,
      maxPlayers: summary.maxPlayers,
      approvedCount: summary.approvedCount,
      waitlistedCount: summary.waitlistedCount,
      spotsRemaining: summary.spotsRemaining,
      timeControl: summary.timeControl,
      description: json['description']?.toString(),
      endsAt: json['ends_at']?.toString(),
      registrationOpenAt: json['registration_open_at']?.toString(),
      registrationCloseAt: json['registration_close_at']?.toString(),
      createdAt: json['created_at']?.toString(),
      myRegistration: json['my_registration'] is Map
          ? TournamentRegistration.fromJson(
              Map<String, Object?>.from(json['my_registration'] as Map),
            )
          : null,
    );
  }
}

class RoundSummary {
  const RoundSummary({
    required this.id,
    required this.tournamentId,
    required this.roundNumber,
    this.title,
    required this.status,
    this.startsAt,
  });

  final String id;
  final String tournamentId;
  final int roundNumber;
  final String? title;
  final String status;
  final String? startsAt;

  factory RoundSummary.fromJson(Map<String, Object?> json) {
    return RoundSummary(
      id: json['id']?.toString() ?? '',
      tournamentId: json['tournament_id']?.toString() ?? '',
      roundNumber: _asInt(json['round_number']),
      title: json['title']?.toString(),
      status: json['status']?.toString() ?? '',
      startsAt: json['starts_at']?.toString(),
    );
  }
}

class StandingRow {
  const StandingRow({
    required this.rank,
    required this.userId,
    required this.username,
    required this.fullName,
    required this.points,
    required this.wins,
    required this.losses,
    required this.draws,
    required this.byes,
    required this.gamesPlayed,
  });

  final int rank;
  final String userId;
  final String username;
  final String fullName;
  final double points;
  final int wins;
  final int losses;
  final int draws;
  final int byes;
  final int gamesPlayed;

  factory StandingRow.fromJson(Map<String, Object?> json) {
    return StandingRow(
      rank: _asInt(json['rank']),
      userId: json['user_id']?.toString() ?? '',
      username: json['username']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
      points: _asDouble(json['points']),
      wins: _asInt(json['wins']),
      losses: _asInt(json['losses']),
      draws: _asInt(json['draws']),
      byes: _asInt(json['byes']),
      gamesPlayed: _asInt(json['games_played']),
    );
  }
}

class LeaderboardRow {
  const LeaderboardRow({
    required this.rank,
    required this.userId,
    required this.username,
    required this.fullName,
    required this.points,
    required this.rating,
    this.wins = 0,
    this.draws = 0,
    this.losses = 0,
    this.gamesPlayed = 0,
  });

  final int rank;
  final String userId;
  final String username;
  final String fullName;
  final double points;
  final int rating;
  final int wins;
  final int draws;
  final int losses;
  final int gamesPlayed;

  factory LeaderboardRow.fromJson(Map<String, Object?> json) {
    return LeaderboardRow(
      rank: _asInt(json['rank']),
      userId: json['user_id']?.toString() ?? '',
      username: json['username']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
      points: _asDouble(json['points']),
      rating: _asInt(json['rating']),
      wins: _asInt(json['wins']),
      draws: _asInt(json['draws']),
      losses: _asInt(json['losses']),
      gamesPlayed: _asInt(json['games_played']),
    );
  }
}

class SeasonSummary {
  const SeasonSummary({
    required this.id,
    required this.name,
    required this.startsAt,
    this.endsAt,
    required this.active,
  });

  final String id;
  final String name;
  final String startsAt;
  final String? endsAt;
  final bool active;

  factory SeasonSummary.fromJson(Map<String, Object?> json) {
    return SeasonSummary(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      startsAt: json['starts_at']?.toString() ?? '',
      endsAt: json['ends_at']?.toString(),
      active: json['active'] == true,
    );
  }
}

class LeaderboardContent {
  const LeaderboardContent({
    this.season,
    this.generatedAt,
    required this.rows,
    required this.limit,
    required this.offset,
    required this.total,
  });

  final SeasonSummary? season;
  final String? generatedAt;
  final List<LeaderboardRow> rows;
  final int limit;
  final int offset;
  final int total;

  factory LeaderboardContent.fromJson(Map<String, Object?> json) {
    return LeaderboardContent(
      season: json['season'] is Map
          ? SeasonSummary.fromJson(
              Map<String, Object?>.from(json['season'] as Map),
            )
          : null,
      generatedAt: json['generated_at']?.toString(),
      rows: _list(json['rows'], LeaderboardRow.fromJson),
      limit: _asInt(json['limit']),
      offset: _asInt(json['offset']),
      total: _asInt(json['total']),
    );
  }
}

class HomeContent {
  const HomeContent({
    required this.announcements,
    required this.latestNews,
    required this.upcomingTournaments,
    required this.leaderboardPreview,
  });

  final List<AnnouncementSummary> announcements;
  final List<ArticleSummary> latestNews;
  final List<TournamentSummary> upcomingTournaments;
  final List<LeaderboardRow> leaderboardPreview;

  factory HomeContent.fromJson(Map<String, Object?> json) {
    return HomeContent(
      announcements: _list(json['announcements'], AnnouncementSummary.fromJson),
      latestNews: _list(json['latest_news'], ArticleSummary.fromJson),
      upcomingTournaments: _list(
        json['upcoming_tournaments'],
        TournamentSummary.fromJson,
      ),
      leaderboardPreview: _list(
        json['leaderboard_preview'],
        LeaderboardRow.fromJson,
      ),
    );
  }
}

class NotificationItem {
  const NotificationItem({
    required this.id,
    required this.type,
    required this.title,
    this.body,
    this.readAt,
    required this.createdAt,
  });

  final String id;
  final String type;
  final String title;
  final String? body;
  final String? readAt;
  final String createdAt;

  factory NotificationItem.fromJson(Map<String, Object?> json) {
    return NotificationItem(
      id: json['id']?.toString() ?? '',
      type: json['type']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      body: json['body']?.toString(),
      readAt: json['read_at']?.toString(),
      createdAt: json['created_at']?.toString() ?? '',
    );
  }
}

class GameSummary {
  const GameSummary({
    required this.id,
    required this.source,
    this.whiteName,
    this.blackName,
    this.result,
    this.event,
    this.playedAt,
    required this.createdAt,
    required this.movesCount,
  });

  final String id;
  final String source;
  final String? whiteName;
  final String? blackName;
  final String? result;
  final String? event;
  final String? playedAt;
  final String createdAt;
  final int movesCount;

  factory GameSummary.fromJson(Map<String, Object?> json) {
    return GameSummary(
      id: json['id']?.toString() ?? '',
      source: json['source']?.toString() ?? '',
      whiteName: json['white_name']?.toString(),
      blackName: json['black_name']?.toString(),
      result: json['result']?.toString(),
      event: json['event']?.toString(),
      playedAt: json['played_at']?.toString(),
      createdAt: json['created_at']?.toString() ?? '',
      movesCount: _asInt(json['moves_count']),
    );
  }
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

double _asDouble(Object? value) {
  if (value is double) {
    return value;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value?.toString() ?? '') ?? 0;
}
