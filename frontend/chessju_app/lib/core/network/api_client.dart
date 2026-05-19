import 'package:chessju_app/core/config/api_config.dart';
import 'package:chessju_app/core/errors/api_error.dart';
import 'package:chessju_app/core/storage/token_storage.dart';
import 'package:dio/dio.dart';
import 'package:uuid/uuid.dart';

class ApiClient {
  ApiClient({
    required ApiConfig config,
    required TokenStorage tokenStorage,
    Dio? dio,
  }) : _tokenStorage = tokenStorage,
       _dio =
           dio ??
           Dio(
             BaseOptions(
               baseUrl: config.apiBaseUrl,
               connectTimeout: const Duration(seconds: 15),
               receiveTimeout: const Duration(seconds: 30),
               headers: const {'Accept': 'application/json'},
             ),
           ) {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          options.headers['X-Request-ID'] ??= const Uuid().v4();
          final tokens = await _tokenStorage.readTokens();
          if (tokens?.accessToken.isNotEmpty ?? false) {
            options.headers['Authorization'] = 'Bearer ${tokens!.accessToken}';
          }
          handler.next(options);
        },
      ),
    );
  }

  final Dio _dio;
  final TokenStorage _tokenStorage;

  Future<T> get<T>(
    String path, {
    Map<String, Object?>? queryParameters,
    required T Function(Object? data) parse,
  }) async {
    return _send(
      () => _dio.get<Object?>(path, queryParameters: queryParameters),
      parse,
    );
  }

  Future<T> post<T>(
    String path, {
    Object? data,
    required T Function(Object? data) parse,
  }) async {
    return _send(() => _dio.post<Object?>(path, data: data), parse);
  }

  Future<T> patch<T>(
    String path, {
    Object? data,
    required T Function(Object? data) parse,
  }) async {
    return _send(() => _dio.patch<Object?>(path, data: data), parse);
  }

  Future<T> delete<T>(
    String path, {
    Object? data,
    required T Function(Object? data) parse,
  }) async {
    return _send(() => _dio.delete<Object?>(path, data: data), parse);
  }

  Future<T> _send<T>(
    Future<Response<Object?>> Function() request,
    T Function(Object? data) parse,
  ) async {
    try {
      final response = await request();
      return parse(response.data);
    } on DioException catch (exception) {
      throw ApiException(ApiError.fromDioException(exception));
    }
  }
}
