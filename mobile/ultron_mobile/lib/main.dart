// mobile/ultron_mobile/lib/main.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'package:ultron_mobile/app/app.dart';
import 'package:ultron_mobile/core/config/app_config.dart';
import 'package:ultron_mobile/core/networking/api_client.dart';
import 'package:ultron_mobile/core/networking/websocket_service.dart';
import 'package:ultron_mobile/core/storage/secure_storage_service.dart';
import 'package:ultron_mobile/features/connection/connection_controller.dart';
import 'package:ultron_mobile/features/chat/chat_controller.dart';
import 'package:ultron_mobile/features/control/control_controller.dart';
import 'package:ultron_mobile/features/proposals/proposal_controller.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  // 1. Instantiate Core Subsystem Singletons
  final config = AppConfig();
  final storage = SecureStorageService();

  final apiClient = ApiClient(config: config, storage: storage);
  final wsService = WebSocketService(config: config, apiClient: apiClient);

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider<ConnectionController>(
          create: (_) => ConnectionController(
            config: config,
            storage: storage,
            apiClient: apiClient,
            wsService: wsService,
          ),
        ),
        ChangeNotifierProvider<ChatController>(
          create: (_) => ChatController(
            apiClient: apiClient,
          ),
        ),
        ChangeNotifierProvider<ControlController>(
          create: (_) => ControlController(
            apiClient: apiClient,
            wsService: wsService,
          ),
        ),
        ChangeNotifierProxyProvider<ConnectionController, ProposalController>(
          create: (context) => ProposalController(
            apiClient: apiClient,
            wsService: wsService,
            connection: context.read<ConnectionController>(),
          ),
          update: (context, connection, previous) =>
              previous ?? ProposalController(
                apiClient: apiClient,
                wsService: wsService,
                connection: connection,
              ),
        ),
      ],
      child: const UltronApp(),
    ),
  );
}
