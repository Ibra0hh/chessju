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
  });

  final int rank;
  final String userId;
  final String username;
  final String fullName;
  final double points;
  final int rating;

  factory LeaderboardRow.fromJson(Map<String, Object?> json) {
    return LeaderboardRow(
      rank: _asInt(json['rank']),
      userId: json['user_id']?.toString() ?? '',
      username: json['username']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
      points: _asDouble(json['points']),
      rating: _asInt(json['rating']),
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
