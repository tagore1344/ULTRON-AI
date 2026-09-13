// mobile/ultron_mobile/lib/core/networking/websocket_service.dart
import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:ultron_mobile/core/config/app_config.dart';
import 'package:ultron_mobile/core/networking/api_client.dart';
import 'package:ultron_mobile/core/models/event.dart';

class WebSocketService {
  final AppConfig config;
  final ApiClient apiClient;

  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  Timer? _pingTimer;

  // Stream controller to broadcast received server events to state listeners
  final StreamController<WsEvent> _eventStreamController = StreamController<WsEvent>.broadcast();

  // State callbacks
  void Function()? onConnected;
  void Function(int? code, String? reason)? onDisconnected;
  void Function(dynamic error)? onError;

  WebSocketService({required this.config, required this.apiClient});

  Stream<WsEvent> get eventStream => _eventStreamController.stream;

  bool get isConnected => _channel != null;

  /// Connect statefully using the single-use 15-second secure ticket handshakes
  Future<void> connect() async {
    if (isConnected) return;

    try {
      // 1. Request short-lived ticket via authenticated REST gateway first
      final ticketData = await apiClient.post("/auth/ws-ticket", {});
      final String ticket = ticketData["ticket"];

      // 2. Connect safely appending ticket in query params
      final wsUri = Uri.parse("${config.wsBaseUrl}?ticket=$ticket");
      _channel = WebSocketChannel.connect(wsUri);

      // 3. Setup message listeners
      _subscription = _channel!.stream.listen(
        (message) => _onMessageReceived(message),
        onError: (e) => _onConnectionError(e),
        onDone: () => _onConnectionClosed(),
      );

      // 4. Initiate heartbeat timer
      _startHeartbeat();
      onConnected?.call();
    } catch (e) {
      _onConnectionError(e);
      rethrow;
    }
  }

  void _onMessageReceived(dynamic message) {
    try {
      final Map<String, dynamic> rawJson = json.decode(message);
      final event = WsEvent.fromJson(rawJson);

      // Internal filter for heartbeat PONG responses (no UI logging)
      if (event.event == "PONG") {
        return;
      }

      _eventStreamController.add(event);
    } catch (_) {}
  }

  void _onConnectionError(dynamic error) {
    onError?.call(error);
    _cleanup();
  }

  void _onConnectionClosed() {
    onDisconnected?.call(_channel?.closeCode, _channel?.closeReason);
    _cleanup();
  }

  void _startHeartbeat() {
    _pingTimer?.cancel();
    _pingTimer = Timer.periodic(const Duration(seconds: 15), (timer) {
      if (isConnected) {
        sendEvent("PING", {});
      }
    });
  }

  /// Sends a validated event envelope payload over WebSocket channel
  void sendEvent(String eventName, Map<String, dynamic> data) {
    if (!isConnected) return;

    final packet = {
      "event": eventName,
      "event_id": "evt_${DateTime.now().millisecondsSinceEpoch}",
      "timestamp": DateTime.now().toUtc().toIso8601String() + "Z",
      "data": data
    };

    _channel!.sink.add(json.encode(packet));
  }

  /// Close and statefully wipe connection channels
  void disconnect() {
    _cleanup();
  }

  void _cleanup() {
    _pingTimer?.cancel();
    _pingTimer = null;

    _subscription?.cancel();
    _subscription = null;

    _channel?.sink.close();
    _channel = null;
  }

  void dispose() {
    _cleanup();
    _eventStreamController.close();
  }
}
