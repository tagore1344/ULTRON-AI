// mobile/ultron_mobile/lib/features/control/control_controller.dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:ultron_mobile/core/networking/api_client.dart';
import 'package:ultron_mobile/core/networking/websocket_service.dart';
import 'package:ultron_mobile/core/models/event.dart';

class ControlController extends ChangeNotifier {
  final ApiClient apiClient;
  final WebSocketService wsService;

  // Live hardware metrics
  Map<String, dynamic> telemetry = {};
  bool _isTelemetryLoading = false;
  Timer? _telemetryTimer;

  // Active command lifecycle states
  String activeCommandId = "";
  String activeCommandStatus = "idle"; // idle, received, authorized, started, completed, failed, rejected
  String activeCommandMessage = "";

  // Active outstanding confirmation popup request details
  Map<String, dynamic>? pendingConfirmation;
  Timer? _countdownTimer;
  int countdownSeconds = 30;

  StreamSubscription? _wsSubscription;

  ControlController({required this.apiClient, required this.wsService}) {
    // 1. Subscribe to stateful WebSocket server events
    _wsSubscription = wsService.eventStream.listen(_onWsEventReceived);
  }

  bool get isTelemetryLoading => _isTelemetryLoading;

  // ==============================================================================
  // TELEMETRY POLLING LIFE-CYCLE
  // ==============================================================================

  void startTelemetryPolling() {
    _telemetryTimer?.cancel();
    _fetchTelemetry(); // Instant initial query
    _telemetryTimer = Timer.periodic(const Duration(seconds: 5), (timer) {
      _fetchTelemetry();
    });
  }

  void stopTelemetryPolling() {
    _telemetryTimer?.cancel();
    _telemetryTimer = null;
  }

  Future<void> _fetchTelemetry() async {
    if (!wsService.isConnected) return;

    try {
      final response = await apiClient.get("/system/status");
      telemetry = response;
      notifyListeners();
    } catch (_) {}
  }

  // ==============================================================================
  // SECURE COMMAND DISPATCH Life-Cycle
  // ==============================================================================

  Future<void> submitCommand(String commandName, Map<String, dynamic> parameters) async {
    activeCommandId = "";
    activeCommandStatus = "sending";
    activeCommandMessage = "Transmitting command payload...";
    notifyListeners();

    try {
      final response = await apiClient.post("/commands", {
        "command": commandName,
        "parameters": parameters
      });

      final bool success = response["success"] ?? false;
      if (success) {
        activeCommandId = response["command_id"];
        activeCommandStatus = response["status"] ?? "completed";
        activeCommandMessage = response["result"]?["message"] ?? "Command completed successfully.";
      } else {
        _setCommandError("Rejected", response["error"]?["message"] ?? "Unknown rejection.");
      }
    } on ForbiddenException catch (e) {
      // Handles blocked high-risk triggers cleanly
      _setCommandError("Rejected", e.message);
    } on ApiException catch (e) {
      if (e.code == "CONFIRMATION_FAILED") {
        _setCommandError("Rejected", e.message);
      } else {
        _setCommandError("Rejected", "Gateway rejected command: ${e.message}");
      }
    } catch (e) {
      _setCommandError("Failed", "Server failed to respond: ${e.toString()}");
    }
  }

  void _setCommandError(String status, String msg) {
    activeCommandStatus = status;
    activeCommandMessage = msg;
    notifyListeners();
  }

  // ==============================================================================
  // EMERGENCY STOP
  // ==============================================================================

  /// Halts all host executions instantly via the authenticated REST gateway,
  /// falling back to the secure authenticated WebSocket channel if REST is
  /// unreachable. Mirrors backend POST /api/v1/agent/emergency-stop semantics.
  Future<bool> triggerEmergencyStop() async {
    try {
      final response = await apiClient.post("/agent/emergency-stop", {});
      activeCommandStatus = "idle";
      activeCommandMessage =
          response["message"] ?? "Emergency stop processed. System reset to IDLE.";
      notifyListeners();
      return true;
    } catch (_) {
      // REST unreachable — fall back to the authenticated WS event channel
      if (wsService.isConnected) {
        wsService.sendEvent("EMERGENCY_STOP", {});
        activeCommandStatus = "idle";
        activeCommandMessage = "Emergency stop transmitted over secure channel.";
        notifyListeners();
        return true;
      }
      activeCommandStatus = "failed";
      activeCommandMessage = "Emergency stop failed: gateway unreachable.";
      notifyListeners();
      return false;
    }
  }

  // ==============================================================================
  // WEBSOCKET CONFIRMATION CALLBACKS
  // ==============================================================================

  void _onWsEventReceived(WsEvent event) {
    // 1. Intercept Confirmation Requests over WebSocket Channel
    if (event.event == "CONFIRMATION_REQUEST") {
      pendingConfirmation = {
        "request_id": event.requestId,
        "command_id": event.commandId,
        "device_id": event.deviceId,
        "command": event.data["command"],
        "description": event.data["description"],
      };

      countdownSeconds = event.data["expires_in"] ?? 30;
      activeCommandStatus = "waiting_confirmation";
      notifyListeners();

      // Setup countdown UI timer
      _countdownTimer?.cancel();
      _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
        if (countdownSeconds > 0) {
          countdownSeconds--;
          notifyListeners();
        } else {
          _countdownTimer?.cancel();
          pendingConfirmation = null;
          notifyListeners();
        }
      });
    }

    // 2. Intercept Expirations or Cancellations
    else if (event.event == "CONFIRMATION_EXPIRED" || event.event == "CONFIRMATION_CANCELLED") {
      _countdownTimer?.cancel();
      pendingConfirmation = null;
      activeCommandStatus = "rejected";
      activeCommandMessage = "Request expired or was canceled by server.";
      notifyListeners();
    }

    // 2.5 Broadcast emergency-stop acknowledgements reset the HUD instantly
    else if (event.event == "EMERGENCY_STOP_TRIGGERED") {
      activeCommandStatus = "idle";
      activeCommandMessage =
          "EMERGENCY STOP executed by ${event.data["cancelled_by"] ?? "host"}. Runtime reset to IDLE.";
      notifyListeners();
    }

    // 3. Track Command Lifecycle Events on HUD
    else if (event.commandId == activeCommandId) {
      if (event.event == "COMMAND_STARTED") {
        activeCommandStatus = "started";
        activeCommandMessage = "Command execution started on laptop host.";
      } else if (event.event == "COMMAND_COMPLETED") {
        activeCommandStatus = "completed";
        activeCommandMessage = "Task successfully completed.";
      } else if (event.event == "COMMAND_FAILED") {
        activeCommandStatus = "failed";
        activeCommandMessage = "Task execution failed on host laptop.";
      }
      notifyListeners();
    }
  }

  /// Submit confirmation decisions statefully matching back to backend envelopes
  void submitDecision(bool approve) {
    if (pendingConfirmation == null) return;

    final reqId = pendingConfirmation!["request_id"];
    final cmdId = pendingConfirmation!["command_id"];
    final decisionStr = approve ? "approved" : "rejected";

    // Broadcast the decision over our secure authenticated WebSocket channel
    wsService.sendEvent("CONFIRMATION_RESPONSE", {
      "request_id": reqId,
      "command_id": cmdId,
      "decision": decisionStr
    });

    _countdownTimer?.cancel();
    pendingConfirmation = null;
    activeCommandStatus = approve ? "approved" : "rejected";
    activeCommandMessage = approve ? "Authorization transmitted. Executing..." : "Command rejected by user.";

    notifyListeners();
  }

  @override
  void dispose() {
    _wsSubscription?.cancel();
    _telemetryTimer?.cancel();
    _countdownTimer?.cancel();
    super.dispose();
  }
}
