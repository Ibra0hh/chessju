import 'package:chessju_app/core/config/api_config.dart';

class RealtimeService {
  const RealtimeService(this._config);

  final ApiConfig _config;

  Uri get streamUri {
    final base = _config.apiBaseUrl;
    return Uri.parse('$base/realtime/stream');
  }

  // Flutter UI integration will subscribe to this endpoint in a later UI pass.
  // The backend already emits authenticated SSE events, and clients should
  // refetch full state after important events.
}
