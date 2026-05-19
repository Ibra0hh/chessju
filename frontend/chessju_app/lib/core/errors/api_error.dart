import 'package:dio/dio.dart';

class ApiError {
  const ApiError({
    required this.code,
    required this.message,
    required this.details,
    this.requestId,
    this.statusCode,
  });

  final String code;
  final String message;
  final Map<String, Object?> details;
  final String? requestId;
  final int? statusCode;

  factory ApiError.fromJson(Map<String, Object?> json, {int? statusCode}) {
    final rawError = json['error'];
    final error = rawError is Map
        ? Map<String, Object?>.from(rawError)
        : Map<String, Object?>.from(json);
    final rawDetails = error['details'];

    return ApiError(
      code: error['code']?.toString() ?? 'server.error',
      message: error['message']?.toString() ?? 'Something went wrong',
      details: rawDetails is Map
          ? Map<String, Object?>.from(rawDetails)
          : const {},
      requestId: error['request_id']?.toString(),
      statusCode: statusCode,
    );
  }

  factory ApiError.fromDioException(DioException exception) {
    final data = exception.response?.data;
    if (data is Map) {
      return ApiError.fromJson(
        Map<String, Object?>.from(data),
        statusCode: exception.response?.statusCode,
      );
    }

    return ApiError(
      code: 'network.error',
      message: exception.message ?? 'Unable to reach ChessJU API',
      details: const {},
      requestId: exception.response?.headers.value('x-request-id'),
      statusCode: exception.response?.statusCode,
    );
  }
}

class ApiException implements Exception {
  const ApiException(this.error);

  final ApiError error;

  @override
  String toString() => '${error.code}: ${error.message}';
}
