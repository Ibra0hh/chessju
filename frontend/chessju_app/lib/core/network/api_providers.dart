import 'package:chessju_app/core/config/api_config.dart';
import 'package:chessju_app/core/network/api_client.dart';
import 'package:chessju_app/core/storage/token_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final apiConfigProvider = Provider<ApiConfig>((ref) {
  return const ApiConfig(baseUrl: ApiConfig.defaultBaseUrl);
});

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(
    config: ref.watch(apiConfigProvider),
    tokenStorage: ref.watch(tokenStorageProvider),
  );
});
