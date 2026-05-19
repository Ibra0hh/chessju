class ApiConfig {
  const ApiConfig({required this.baseUrl});

  static const defaultBaseUrl = String.fromEnvironment(
    'CHESSJU_API_BASE_URL',
    defaultValue: 'http://localhost:8001',
  );

  final String baseUrl;

  String get apiBaseUrl {
    final normalized = baseUrl.endsWith('/')
        ? baseUrl.substring(0, baseUrl.length - 1)
        : baseUrl;
    return '$normalized/api/v1';
  }
}
