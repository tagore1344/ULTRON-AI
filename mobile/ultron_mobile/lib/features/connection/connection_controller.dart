// mobile/ultron_mobile/lib/features/connection/connection_controller.dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:ultron_mobile/core/config/app_config.dart';
import 'package:ultron_mobile/core/networking/api_client.dart';
import 'package:ultron_mobile/core/networking/websocket_service.dart';
import 'package:ultron_mobile/core/storage/secure_storage_service.dart';

enum ConnectionState {
  disconnected,
  connecting,
  connected,
  reconnecting,
  error,
  pairing,
  revoked
}

class ConnectionController extends ChangeNotifier {
  final AppConfig config;
  final SecureStorageService storage;
  final ApiClient apiClient;
  final WebSocketService wsService;

  ConnectionState _state = ConnectionState.disconnected;
  String _errorMessage = "";
  bool _isPaired = false;
  String? _pairedDeviceName;

  Timer? _reconnectTimer;
  int _reconnectDelaySeconds = 1;

  ConnectionController({
    required this.config,
    required this.storage,
    required this.apiClient,
    required this.wsService,
  }) {
    // Register WS Callbacks
    wsService.onConnected = _onWsConnected;
    wsService.onDisconnected = _onWsDisconnected;
    wsService.onError = _onWsError;

    // Run initial boot scan
    _bootstrap();
  }

  ConnectionState get state => _state;
  String get errorMessage => _errorMessage;
  bool get isPaired => _isPaired;
  String? get pairedDeviceName => _pairedDeviceName;

  void _setState(ConnectionState newState, {String error = ""}) {
    _state = newState;
    _errorMessage = error;
    notifyListeners();
  }

  /// Initial app load boot scan
  Future<void> _bootstrap() async {
    final token = await storage.loadToken();
    final savedUrl = await storage.loadHostUrl();
    final deviceId = await storage.loadDeviceId();

    if (token != null && savedUrl != null && deviceId != null) {
      _isPaired = true;
      _pairedDeviceName = config.deviceName;

      // Load saved URL configs
      try {
        final parsedUrl = Uri.parse(savedUrl);
        config.host = parsedUrl.host;
        config.port = parsedUrl.port;
      } catch (_) {}

      _setState(ConnectionState.disconnected);
      await connect();
    } else {
      _isPaired = false;
      _setState(ConnectionState.disconnected);
    }
  }

  /// Submit Pair Request
  Future<void> pairDevice(String hostAddress, String pairingCode, String customDeviceName) async {
    _setState(ConnectionState.pairing);

    try {
      // 1. Update config address temporarily for pair handshake check
      final parsedUri = Uri.parse(hostAddress.startsWith("http") ? hostAddress : "http://$hostAddress");
      config.host = parsedUri.host;
      config.port = parsedUri.port == 0 ? 8000 : parsedUri.port;
      config.deviceName = customDeviceName;

      // 2. Query REST pairing endpoint
      final response = await apiClient.post("/auth/pair", {
        "pairing_code": pairingCode,
        "device_name": customDeviceName,
        "device_type": "android"
      });

      final bool success = response["success"] ?? false;
      if (success) {
        final token = response["access_token"];
        final deviceId = response["device"]["device_id"];
        final hostUrl = "http://${config.host}:${config.port}";

        // 3. Save issued credentials securely
        await storage.saveToken(token);
        await storage.saveDeviceId(deviceId);
        await storage.saveHostUrl(hostUrl);

        _isPaired = true;
        _pairedDeviceName = customDeviceName;
        _setState(ConnectionState.disconnected);

        // 4. Connect Websockets instantly
        await connect();
      } else {
        throw ApiException("PAIRING_FAILED", "Failed to pair device.");
      }
    } catch (e) {
      _isPaired = false;
      _setState(ConnectionState.error, error: e.toString());
      rethrow;
    }
  }

  /// Stateful Connect Loop
  Future<void> connect() async {
    if (_state == ConnectionState.connected) return;

    if (_state != ConnectionState.reconnecting) {
      _setState(ConnectionState.connecting);
    }

    try {
      await wsService.connect();
    } catch (e) {
      _setState(ConnectionState.error, error: "Gateway connection failed.");
      _scheduleReconnection();
    }
  }

  void _onWsConnected() {
    _reconnectDelaySeconds = 1; // Reset backoff delay
    _reconnectTimer?.cancel();
    _setState(ConnectionState.connected);
  }

  void _onWsDisconnected(int? code, String? reason) {
    if (code == 1008) {
      // 1008 indicates policy violations / access revocations on handshakes
      _onRevocationTriggered();
    } else {
      _setState(ConnectionState.reconnecting);
      _scheduleReconnection();
    }
  }

  void _onWsError(dynamic error) {
    _setState(ConnectionState.reconnecting);
    _scheduleReconnection();
  }

  void _scheduleReconnection() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(seconds: _reconnectDelaySeconds), () async {
      if (_isPaired && _state != ConnectionState.connected) {
        logger.info("Attempting automatic reconnection delay: %ds", _reconnectDelaySeconds);

        // Exponential Backoff calculation
        _reconnectDelaySeconds = (_reconnectDelaySeconds * 2).clamp(1, 30);
        await connect();
      }
    });
  }

  void _onRevocationTriggered() async {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;

    // Safely delete compromised credentials instantly
    await storage.clearAll();
    _isPaired = false;
    _pairedDeviceName = null;

    _setState(ConnectionState.revoked, error: "Access revoked by Laptop host.");
  }

  /// Safe Unpair / Logoff Action
  Future<void> unpairDevice() async {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;

    try {
      final deviceId = await storage.loadDeviceId();
      if (deviceId != null) {
        // Log clean revocation query back to server if connected
        await apiClient.delete("/devices/$deviceId");
      }
    } catch (_) {}

    wsService.disconnect();
    await storage.clearAll();

    _isPaired = false;
    _pairedDeviceName = null;
    _setState(ConnectionState.disconnected);
  }

  @override
  void dispose() {
    _reconnectTimer?.cancel();
    super.dispose();
  }
}

// Global logger helper wrapper
class logger {
  static void info(String msg, [dynamic p1]) {
    debugPrint("[ConnectionController] INFO: " + msg.replaceAll("%ds", p1?.toString() ?? ""));
  }
}
