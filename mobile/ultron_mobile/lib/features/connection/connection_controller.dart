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
  revoked,
}

class ConnectionController extends ChangeNotifier {
  final AppConfig config;
  final SecureStorageService storage;
  final ApiClient apiClient;
  final WebSocketService wsService;

  ConnectionState _state = ConnectionState.disconnected;
  String _errorMessage = '';
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
    wsService.onConnected = _onWsConnected;
    wsService.onDisconnected = _onWsDisconnected;
    wsService.onError = _onWsError;
    _bootstrap();
  }

  ConnectionState get state => _state;
  String get errorMessage => _errorMessage;
  bool get isPaired => _isPaired;
  String? get pairedDeviceName => _pairedDeviceName;
  bool get isConnected => _state == ConnectionState.connected;

  void _setState(ConnectionState state, {String error = ''}) {
    _state = state;
    _errorMessage = error;
    notifyListeners();
  }

  Future<void> _bootstrap() async {
    final token = await storage.loadToken();
    final savedUrl = await storage.loadHostUrl();
    final deviceId = await storage.loadDeviceId();

    if (token == null || savedUrl == null || deviceId == null) {
      _isPaired = false;
      _setState(ConnectionState.disconnected);
      return;
    }

    _isPaired = true;
    _pairedDeviceName = config.deviceName;
    try {
      final parsedUrl = Uri.parse(savedUrl);
      config.host = parsedUrl.host;
      config.port = parsedUrl.port == 0 ? 8000 : parsedUrl.port;
    } catch (_) {}

    _setState(ConnectionState.disconnected);
    await connect();
  }

  Future<void> pairDevice(
    String hostAddress,
    String pairingCode,
    String customDeviceName,
  ) async {
    _setState(ConnectionState.pairing);
    try {
      final parsedUri = Uri.parse(
        hostAddress.startsWith('http') ? hostAddress : 'http://$hostAddress',
      );
      config.host = parsedUri.host;
      config.port = parsedUri.port == 0 ? 8000 : parsedUri.port;
      config.deviceName = customDeviceName;

      final response = await apiClient.post('/auth/pair', {
        'pairing_code': pairingCode,
        'device_name': customDeviceName,
        'device_type': 'android',
      });

      final success = response['success'] ?? false;
      if (!success) {
        throw ApiException('PAIRING_FAILED', 'Failed to pair device.');
      }

      await storage.saveToken(response['access_token']);
      await storage.saveDeviceId(response['device']['device_id']);
      await storage.saveHostUrl('http://${config.host}:${config.port}');

      _isPaired = true;
      _pairedDeviceName = customDeviceName;
      _setState(ConnectionState.disconnected);
      await connect();
    } catch (e) {
      _isPaired = false;
      _setState(ConnectionState.error, error: e.toString());
      rethrow;
    }
  }

  Future<void> connect() async {
    if (_state == ConnectionState.connected) return;
    if (_state != ConnectionState.reconnecting) {
      _setState(ConnectionState.connecting);
    }

    try {
      await wsService.connect();
    } catch (_) {
      _setState(ConnectionState.error, error: 'Gateway connection failed.');
      _scheduleReconnection();
    }
  }

  void _onWsConnected() {
    _reconnectDelaySeconds = 1;
    _reconnectTimer?.cancel();
    _setState(ConnectionState.connected);
  }

  void _onWsDisconnected(int? code, String? reason) {
    if (code == 1008) {
      _onRevocationTriggered();
      return;
    }
    _setState(ConnectionState.reconnecting);
    _scheduleReconnection();
  }

  void _onWsError(dynamic error) {
    _setState(ConnectionState.reconnecting);
    _scheduleReconnection();
  }

  void _scheduleReconnection() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(
      Duration(seconds: _reconnectDelaySeconds),
      () async {
        if (_isPaired && _state != ConnectionState.connected) {
          _reconnectDelaySeconds = (_reconnectDelaySeconds * 2).clamp(1, 30);
          await connect();
        }
      },
    );
  }

  Future<void> _onRevocationTriggered() async {
    _reconnectTimer?.cancel();
    await storage.clearAll();
    _isPaired = false;
    _pairedDeviceName = null;
    _setState(ConnectionState.revoked, error: 'Access revoked by TAG host.');
  }

  Future<void> unpairDevice() async {
    _reconnectTimer?.cancel();
    try {
      final deviceId = await storage.loadDeviceId();
      if (deviceId != null) {
        await apiClient.delete('/devices/$deviceId');
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
