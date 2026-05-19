import 'package:chessju_app/core/errors/api_error.dart';
import 'package:chessju_app/core/network/api_providers.dart';
import 'package:chessju_app/core/storage/token_storage.dart';
import 'package:chessju_app/features/auth/data/auth_models.dart';
import 'package:chessju_app/features/auth/data/auth_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(
    apiClient: ref.watch(apiClientProvider),
    tokenStorage: ref.watch(tokenStorageProvider),
  );
});

final authControllerProvider = NotifierProvider<AuthController, AuthState>(
  AuthController.new,
);

enum AuthStatus { unknown, loading, authenticated, unauthenticated }

class AuthState {
  const AuthState({
    this.status = AuthStatus.unknown,
    this.user,
    this.errorMessage,
  });

  final AuthStatus status;
  final CurrentUser? user;
  final String? errorMessage;

  bool get isAuthenticated => status == AuthStatus.authenticated;

  AuthState copyWith({
    AuthStatus? status,
    CurrentUser? user,
    String? errorMessage,
    bool clearUser = false,
    bool clearError = false,
  }) {
    return AuthState(
      status: status ?? this.status,
      user: clearUser ? null : user ?? this.user,
      errorMessage: clearError ? null : errorMessage ?? this.errorMessage,
    );
  }
}

class AuthController extends Notifier<AuthState> {
  @override
  AuthState build() => const AuthState();

  AuthRepository get _repository => ref.read(authRepositoryProvider);

  Future<void> restoreSession() async {
    state = state.copyWith(status: AuthStatus.loading, clearError: true);
    final tokens = await _repository.storedTokens();
    if (tokens == null) {
      state = const AuthState(status: AuthStatus.unauthenticated);
      return;
    }

    try {
      final user = await _repository.currentUser();
      state = AuthState(status: AuthStatus.authenticated, user: user);
    } on ApiException {
      await _repository.logout();
      state = const AuthState(status: AuthStatus.unauthenticated);
    }
  }

  Future<bool> login({required String email, required String password}) async {
    state = state.copyWith(status: AuthStatus.loading, clearError: true);
    try {
      final response = await _repository.login(
        email: email,
        password: password,
      );
      state = AuthState(status: AuthStatus.authenticated, user: response.user);
      return true;
    } on ApiException catch (exception) {
      state = AuthState(
        status: AuthStatus.unauthenticated,
        errorMessage: exception.error.message,
      );
      return false;
    }
  }

  Future<bool> register({
    required String email,
    required String password,
    required String username,
    required String fullName,
    String? universityId,
    String? chesscomUsername,
  }) async {
    state = state.copyWith(status: AuthStatus.loading, clearError: true);
    try {
      final response = await _repository.register(
        email: email,
        password: password,
        username: username,
        fullName: fullName,
        universityId: universityId,
        chesscomUsername: chesscomUsername,
      );
      state = AuthState(status: AuthStatus.authenticated, user: response.user);
      return true;
    } on ApiException catch (exception) {
      state = AuthState(
        status: AuthStatus.unauthenticated,
        errorMessage: exception.error.message,
      );
      return false;
    }
  }

  Future<void> logout() async {
    state = state.copyWith(status: AuthStatus.loading, clearError: true);
    await _repository.logout();
    state = const AuthState(status: AuthStatus.unauthenticated);
  }
}
