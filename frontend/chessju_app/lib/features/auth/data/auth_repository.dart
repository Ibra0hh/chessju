import 'package:chessju_app/core/network/api_client.dart';
import 'package:chessju_app/core/storage/token_storage.dart';
import 'package:chessju_app/features/auth/data/auth_models.dart';

class AuthRepository {
  const AuthRepository({
    required ApiClient apiClient,
    required TokenStorage tokenStorage,
  }) : _apiClient = apiClient,
       _tokenStorage = tokenStorage;

  final ApiClient _apiClient;
  final TokenStorage _tokenStorage;

  Future<AuthResponse> register({
    required String email,
    required String password,
    required String username,
    required String fullName,
    String? universityId,
    String? chesscomUsername,
  }) async {
    final response = await _apiClient.post<AuthResponse>(
      '/auth/register',
      data: {
        'email': email,
        'password': password,
        'username': username,
        'full_name': fullName,
        if (universityId?.isNotEmpty ?? false) 'university_id': universityId,
        if (chesscomUsername?.isNotEmpty ?? false)
          'chesscom_username': chesscomUsername,
      },
      parse: _parseAuthResponse,
    );
    await _tokenStorage.saveTokens(response.tokens);
    return response;
  }

  Future<AuthResponse> login({
    required String email,
    required String password,
  }) async {
    final response = await _apiClient.post<AuthResponse>(
      '/auth/login',
      data: {'email': email, 'password': password},
      parse: _parseAuthResponse,
    );
    await _tokenStorage.saveTokens(response.tokens);
    return response;
  }

  Future<AuthResponse?> refresh() async {
    final tokens = await _tokenStorage.readTokens();
    if (tokens == null) {
      return null;
    }

    final response = await _apiClient.post<AuthResponse>(
      '/auth/refresh',
      data: {'refresh_token': tokens.refreshToken},
      parse: _parseAuthResponse,
    );
    await _tokenStorage.saveTokens(response.tokens);
    return response;
  }

  Future<CurrentUser> currentUser() async {
    return _apiClient.get<CurrentUser>(
      '/auth/me',
      parse: (data) => CurrentUser.fromJson(_asMap(data)),
    );
  }

  Future<void> logout() async {
    final tokens = await _tokenStorage.readTokens();
    if (tokens != null) {
      try {
        await _apiClient.post<void>(
          '/auth/logout',
          data: {'refresh_token': tokens.refreshToken},
          parse: (_) {},
        );
      } on Object {
        // Local logout must still clear tokens if the network call fails.
      }
    }
    await _tokenStorage.clearTokens();
  }

  Future<AuthTokens?> storedTokens() {
    return _tokenStorage.readTokens();
  }

  AuthResponse _parseAuthResponse(Object? data) {
    return AuthResponse.fromJson(_asMap(data));
  }

  Map<String, Object?> _asMap(Object? data) {
    return Map<String, Object?>.from(data as Map? ?? const {});
  }
}
