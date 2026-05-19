class Pagination {
  const Pagination({
    required this.limit,
    required this.offset,
    required this.count,
    this.total,
  });

  final int limit;
  final int offset;
  final int count;
  final int? total;

  factory Pagination.fromJson(Map<String, Object?> json) {
    final rawPagination = json['pagination'];
    if (rawPagination is Map) {
      final pagination = Map<String, Object?>.from(rawPagination);
      return Pagination(
        limit: _asInt(pagination['limit']),
        offset: _asInt(pagination['offset']),
        count: _asInt(pagination['count']),
        total: pagination['total'] == null ? null : _asInt(pagination['total']),
      );
    }

    final items = json['items'];
    final count = items is List ? items.length : _asInt(json['count']);
    return Pagination(
      limit: _asInt(json['limit']),
      offset: _asInt(json['offset']),
      count: count,
      total: json['total'] == null ? null : _asInt(json['total']),
    );
  }

  static int _asInt(Object? value) {
    if (value is int) {
      return value;
    }
    if (value is num) {
      return value.toInt();
    }
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }
}

class PaginatedResponse<T> {
  const PaginatedResponse({required this.items, required this.pagination});

  final List<T> items;
  final Pagination pagination;

  factory PaginatedResponse.fromJson(
    Map<String, Object?> json,
    T Function(Map<String, Object?> item) parseItem,
  ) {
    final rawItems = json['items'];
    final items = rawItems is List
        ? rawItems
              .whereType<Map>()
              .map((item) => parseItem(Map<String, Object?>.from(item)))
              .toList()
        : <T>[];

    return PaginatedResponse(
      items: items,
      pagination: Pagination.fromJson({...json, 'count': items.length}),
    );
  }
}
