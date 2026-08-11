// mobile/ultron_mobile/lib/core/config/app_config.dart
import 'package:flutter/foundation.dart';

class AppConfig {
  static const String defaultHost = "192.168.1.10";
  static const int defaultPort = 8000;
  static const String defaultDeviceName = "Android Device";

  // Active configurations in memory (editable by settings)
  String host;
  int port;
  String deviceName;
  bool isProduction;

  AppConfig({
    this.host = defaultHost,
    this.port = defaultPort,
    this.deviceName = defaultDeviceName,
    this.isProduction = !kDebugMode,
  });

  String get restBaseUrl {
    return "http://$host:$port/api/v1";
  }

  String get wsBaseUrl {
    return "ws://$host:$port/ws";
  }
}
