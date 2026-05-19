import 'package:chessju_app/shared/models/content_models.dart';

const standardInitialFen =
    'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

class GameDetail extends GameSummary {
  const GameDetail({
    required super.id,
    required super.source,
    super.whiteName,
    super.blackName,
    super.result,
    super.event,
    super.site,
    super.date,
    super.round,
    super.ecoCode,
    super.openingName,
    super.timeControl,
    super.playedAt,
    required super.createdAt,
    required super.movesCount,
    this.metadata = const {},
    this.initialFen,
    this.finalFen,
    this.moves = const [],
  });

  final Map<String, String> metadata;
  final String? initialFen;
  final String? finalFen;
  final List<GameMove> moves;

  String get playableInitialFen =>
      (initialFen?.isNotEmpty ?? false) ? initialFen! : standardInitialFen;

  factory GameDetail.fromJson(Map<String, Object?> json) {
    return GameDetail(
      id: json['id']?.toString() ?? '',
      source: json['source']?.toString() ?? '',
      whiteName: json['white_name']?.toString(),
      blackName: json['black_name']?.toString(),
      result: json['result']?.toString(),
      event: json['event']?.toString(),
      playedAt: json['played_at']?.toString(),
      createdAt: json['created_at']?.toString() ?? '',
      movesCount: _asInt(json['moves_count']),
      site: json['site']?.toString(),
      date: json['date']?.toString(),
      round: json['round']?.toString(),
      ecoCode: json['eco_code']?.toString(),
      openingName: json['opening_name']?.toString(),
      timeControl: json['time_control']?.toString(),
      metadata: _stringMap(json['metadata']),
      initialFen: json['initial_fen']?.toString(),
      finalFen: json['final_fen']?.toString(),
      moves: _list(json['moves'], GameMove.fromJson),
    );
  }
}

class GameMove {
  const GameMove({
    this.id,
    required this.plyNumber,
    required this.moveNumber,
    required this.side,
    required this.san,
    required this.uci,
    required this.fenBefore,
    required this.fenAfter,
    required this.isCheck,
    required this.isCheckmate,
    this.comment,
    this.createdAt,
  });

  final String? id;
  final int plyNumber;
  final int moveNumber;
  final String side;
  final String san;
  final String uci;
  final String fenBefore;
  final String fenAfter;
  final bool isCheck;
  final bool isCheckmate;
  final String? comment;
  final String? createdAt;

  factory GameMove.fromJson(Map<String, Object?> json) {
    return GameMove(
      id: json['id']?.toString(),
      plyNumber: _asInt(json['ply_number']),
      moveNumber: _asInt(json['move_number']),
      side: json['side']?.toString() ?? '',
      san: json['san']?.toString() ?? '',
      uci: json['uci']?.toString() ?? '',
      fenBefore: json['fen_before']?.toString() ?? '',
      fenAfter: json['fen_after']?.toString() ?? '',
      isCheck: json['is_check'] == true,
      isCheckmate: json['is_checkmate'] == true,
      comment: json['comment']?.toString(),
      createdAt: json['created_at']?.toString(),
    );
  }
}

class PgnImport {
  const PgnImport({
    required this.id,
    required this.userId,
    required this.source,
    required this.status,
    this.fileId,
    this.gameId,
    this.errorMessage,
    required this.createdAt,
    this.completedAt,
  });

  final String id;
  final String userId;
  final String source;
  final String status;
  final String? fileId;
  final String? gameId;
  final String? errorMessage;
  final String createdAt;
  final String? completedAt;

  factory PgnImport.fromJson(Map<String, Object?> json) {
    return PgnImport(
      id: json['id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      source: json['source']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      fileId: json['file_id']?.toString(),
      gameId: json['game_id']?.toString(),
      errorMessage: json['error_message']?.toString(),
      createdAt: json['created_at']?.toString() ?? '',
      completedAt: json['completed_at']?.toString(),
    );
  }
}

class AnalysisJob {
  const AnalysisJob({
    required this.id,
    required this.gameId,
    required this.status,
    required this.engineName,
    this.engineVersion,
    this.depth,
    this.timeLimitMs,
    required this.createdAt,
    this.startedAt,
    this.completedAt,
    this.errorMessage,
  });

  final String id;
  final String gameId;
  final String status;
  final String engineName;
  final String? engineVersion;
  final int? depth;
  final int? timeLimitMs;
  final String createdAt;
  final String? startedAt;
  final String? completedAt;
  final String? errorMessage;

  bool get isActive => status == 'queued' || status == 'running';

  factory AnalysisJob.fromJson(Map<String, Object?> json) {
    return AnalysisJob(
      id: json['id']?.toString() ?? '',
      gameId: json['game_id']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      engineName: json['engine_name']?.toString() ?? 'stockfish',
      engineVersion: json['engine_version']?.toString(),
      depth: _nullableInt(json['depth']),
      timeLimitMs: _nullableInt(json['time_limit_ms']),
      createdAt: json['created_at']?.toString() ?? '',
      startedAt: json['started_at']?.toString(),
      completedAt: json['completed_at']?.toString(),
      errorMessage: json['error_message']?.toString(),
    );
  }
}

class GameAnalysisState {
  const GameAnalysisState({this.report, this.job});

  final AnalysisReport? report;
  final AnalysisJob? job;

  factory GameAnalysisState.fromJson(Map<String, Object?> json) {
    return GameAnalysisState(
      report: json['report'] is Map
          ? AnalysisReport.fromJson(
              Map<String, Object?>.from(json['report'] as Map),
            )
          : null,
      job: json['job'] is Map
          ? AnalysisJob.fromJson(Map<String, Object?>.from(json['job'] as Map))
          : null,
    );
  }
}

class AnalysisReport {
  const AnalysisReport({
    required this.id,
    required this.gameId,
    required this.analysisJobId,
    this.whiteAccuracy,
    this.blackAccuracy,
    this.summary = const {},
    this.finalEvaluation,
    required this.createdAt,
    this.moves = const [],
  });

  final String id;
  final String gameId;
  final String analysisJobId;
  final double? whiteAccuracy;
  final double? blackAccuracy;
  final Map<String, Object?> summary;
  final Evaluation? finalEvaluation;
  final String createdAt;
  final List<AnalysisMoveEvaluation> moves;

  factory AnalysisReport.fromJson(Map<String, Object?> json) {
    return AnalysisReport(
      id: json['id']?.toString() ?? '',
      gameId: json['game_id']?.toString() ?? '',
      analysisJobId: json['analysis_job_id']?.toString() ?? '',
      whiteAccuracy: _nullableDouble(json['white_accuracy']),
      blackAccuracy: _nullableDouble(json['black_accuracy']),
      summary: _objectMap(json['summary']),
      finalEvaluation: json['final_evaluation'] is Map
          ? Evaluation.fromJson(
              Map<String, Object?>.from(json['final_evaluation'] as Map),
            )
          : null,
      createdAt: json['created_at']?.toString() ?? '',
      moves: _list(json['moves'], AnalysisMoveEvaluation.fromJson),
    );
  }
}

class AnalysisMoveEvaluation {
  const AnalysisMoveEvaluation({
    this.id,
    this.gameMoveId,
    required this.plyNumber,
    this.moveNumber,
    required this.side,
    required this.san,
    required this.uci,
    this.evaluationBefore,
    this.evaluationAfter,
    this.bestMoveUci,
    this.bestMoveSan,
    this.principalVariation = const [],
    this.centipawnLoss,
    this.classification,
    this.createdAt,
  });

  final String? id;
  final String? gameMoveId;
  final int plyNumber;
  final int? moveNumber;
  final String side;
  final String san;
  final String uci;
  final Evaluation? evaluationBefore;
  final Evaluation? evaluationAfter;
  final String? bestMoveUci;
  final String? bestMoveSan;
  final List<String> principalVariation;
  final int? centipawnLoss;
  final String? classification;
  final String? createdAt;

  factory AnalysisMoveEvaluation.fromJson(Map<String, Object?> json) {
    return AnalysisMoveEvaluation(
      id: json['id']?.toString(),
      gameMoveId: json['game_move_id']?.toString(),
      plyNumber: _asInt(json['ply_number']),
      moveNumber: _nullableInt(json['move_number']),
      side: json['side']?.toString() ?? '',
      san: json['san']?.toString() ?? '',
      uci: json['uci']?.toString() ?? '',
      evaluationBefore: json['evaluation_before'] is Map
          ? Evaluation.fromJson(
              Map<String, Object?>.from(json['evaluation_before'] as Map),
            )
          : null,
      evaluationAfter: json['evaluation_after'] is Map
          ? Evaluation.fromJson(
              Map<String, Object?>.from(json['evaluation_after'] as Map),
            )
          : null,
      bestMoveUci: json['best_move_uci']?.toString(),
      bestMoveSan: json['best_move_san']?.toString(),
      principalVariation: _stringList(json['principal_variation']),
      centipawnLoss: _nullableInt(json['centipawn_loss']),
      classification: json['classification']?.toString(),
      createdAt: json['created_at']?.toString(),
    );
  }
}

class Evaluation {
  const Evaluation({this.type, this.value, this.display});

  final String? type;
  final num? value;
  final String? display;

  String get label {
    if (display?.isNotEmpty ?? false) {
      return display!;
    }
    if (type == 'mate' && value != null) {
      return 'M$value';
    }
    if (value != null) {
      final cp = value!.toDouble() / 100;
      final sign = cp > 0 ? '+' : '';
      return '$sign${cp.toStringAsFixed(2)}';
    }
    return '-';
  }

  factory Evaluation.fromJson(Map<String, Object?> json) {
    return Evaluation(
      type: json['type']?.toString(),
      value: json['value'] is num
          ? json['value'] as num
          : num.tryParse(json['value']?.toString() ?? ''),
      display: json['display']?.toString(),
    );
  }
}

String analysisClassificationLabel(String? classification) {
  if (classification == null || classification.isEmpty) {
    return 'Unknown';
  }
  return classification
      .split('_')
      .map(
        (part) => part.isEmpty
            ? part
            : '${part[0].toUpperCase()}${part.substring(1)}',
      )
      .join(' ');
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

Map<String, String> _stringMap(Object? value) {
  if (value is! Map) {
    return const {};
  }
  return Map<String, Object?>.from(
    value,
  ).map((key, item) => MapEntry(key, item?.toString() ?? ''));
}

Map<String, Object?> _objectMap(Object? value) {
  if (value is! Map) {
    return const {};
  }
  return Map<String, Object?>.from(value);
}

List<String> _stringList(Object? value) {
  if (value is! List) {
    return const [];
  }
  return value.map((item) => item.toString()).toList();
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

double? _nullableDouble(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value.toString());
}
