// mobile/ultron_mobile/lib/features/control/control_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:ultron_mobile/app/theme.dart';
import 'package:ultron_mobile/features/control/control_controller.dart';

class ControlScreen extends StatefulWidget {
  const ControlScreen({super.key});

  @override
  State<ControlScreen> createState() => _ControlScreenState();
}

class _ControlScreenState extends State<ControlScreen> {
  @override
  void initState() {
    super.initState();
    // Start polling telemetry variables statefully on load
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<ControlController>(context, listen: false).startTelemetryPolling();
    });
  }

  @override
  void dispose() {
    // Stop polling to preserve network and battery when not visible
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        Provider.of<ControlController>(context, listen: false).stopTelemetryPolling();
      }
    });
    super.dispose();
  }

  void _onSafeCommandPressed(ControlController controller, String name) async {
    await controller.submitCommand(name, {});
  }

  void _onConfirmationCommandPressed(ControlController controller, String name, Map<String, dynamic> params) async {
    await controller.submitCommand(name, params);
  }

  @override
  Widget build(BuildContext context) {
    final controller = Provider.of<ControlController>(context);

    return Scaffold(
      backgroundColor: UltronTheme.obsidianBackground,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text(
          "LAPTOP NATIVE CONTROLS",
          style: TextStyle(fontFamily: 'Consolas', fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 1.5),
        ),
      ),
      body: Stack(
        children: [
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // --- TELEMETRY CARD METER ---
                  _buildTelemetryDashboard(context, controller.telemetry),
                  const SizedBox(height: 24),

                  // --- COMMAND LIFECYCLE AUDIT LOG ---
                  _buildAuditLogCard(context, controller),
                  const SizedBox(height: 24),

                  // --- SAFE ACTIONS ---
                  const Text(
                    "SAFE OPERATIONS (IMMEDIATE)",
                    style: TextStyle(fontFamily: 'Consolas', fontSize: 11, color: UltronTheme.cleanGrey),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(child: _buildButton(context, "GET TIME", () => _onSafeCommandPressed(controller, "get_time"))),
                      const SizedBox(width: 12),
                      Expanded(child: _buildButton(context, "GET DATE", () => _onSafeCommandPressed(controller, "get_date"))),
                    ],
                  ),
                  const SizedBox(height: 24),

                  // --- CONFIRMATION REQUIRED ACTIONS ---
                  const Text(
                    "HOST UTILITIES (CONFIRMATION)",
                    style: TextStyle(fontFamily: 'Consolas', fontSize: 11, color: UltronTheme.cleanGrey),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: _buildButton(
                          context,
                          "LAUNCH CHROME",
                          () => _onConfirmationCommandPressed(controller, "launch_application", {"application": "chrome"}),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _buildButton(
                          context,
                          "TAKE SCREENSHOT",
                          () => _onConfirmationCommandPressed(controller, "screenshot", {}),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: _buildButton(
                          context,
                          "VOLUME UP",
                          () => _onConfirmationCommandPressed(controller, "volume_up", {}),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _buildButton(
                          context,
                          "VOLUME DOWN",
                          () => _onConfirmationCommandPressed(controller, "volume_down", {}),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 30),
                ],
              ),
            ),
          ),

          // --- REAL-TIME MODAL DIALOG CONFIRMATION OVERLAY ---
          if (controller.pendingConfirmation != null)
            _buildConfirmationDialogOverlay(context, controller),
        ],
      ),
    );
  }

  Widget _buildTelemetryDashboard(BuildContext context, Map<String, dynamic> data) {
    // Process default and fallback structures safely
    final cpuPercent = data["cpu"]?["usage_percent"] ?? 0.0;
    final ramPercent = data["memory"]?["usage_percent"] ?? 0.0;

    final gpuObj = data["gpu"] ?? {};
    final bool gpuAvailable = gpuObj["available"] ?? false;
    final gpuPercent = gpuObj["usage_percent"] ?? 0;
    final gpuName = gpuObj["name"] ?? "N/A";

    final battObj = data["battery"] ?? {};
    final bool battAvailable = battObj["available"] ?? false;
    final battPercent = battObj["percent"] ?? 0;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: UltronTheme.spaceSurface,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            "LIVE HARDWARE TELEMETRY",
            style: TextStyle(fontFamily: 'Consolas', fontSize: 11, color: UltronTheme.cyanAccent, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 20),

          // CPU Meter
          _buildMeterBar("CPU UTILIZATION", cpuPercent / 100.0, "${cpuPercent.toStringAsFixed(1)}%"),
          const SizedBox(height: 16),

          // RAM Meter
          _buildMeterBar("RAM UTILIZATION", ramPercent / 100.0, "${ramPercent.toStringAsFixed(1)}%"),
          const SizedBox(height: 16),

          // GPU Meter (NVIDIA)
          gpuAvailable
              ? _buildMeterBar("GPU ($gpuName)", gpuPercent / 100.0, "$gpuPercent%")
              : _buildUnavailableRow("NVIDIA GPU DETECTED", "UNAVAILABLE"),
          const SizedBox(height: 16),

          // Battery Meter
          battAvailable
              ? _buildMeterBar("BATTERY CORE CHARGE", battPercent / 100.0, "$battPercent%")
              : _buildUnavailableRow("LAPTOP BATTERY CELL", "UNAVAILABLE / AC POWER"),
        ],
      ),
    );
  }

  Widget _buildMeterBar(String label, double ratio, String valueText) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              label,
              style: const TextStyle(fontFamily: 'Consolas', fontSize: 9, color: UltronTheme.cleanGrey),
            ),
            Text(
              valueText,
              style: const TextStyle(fontFamily: 'Consolas', fontSize: 11, color: Colors.white, fontWeight: FontWeight.bold),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: ratio,
            backgroundColor: UltronTheme.obsidianBackground,
            color: UltronTheme.cyanAccent,
            minHeight: 8,
          ),
        ),
      ],
    );
  }

  Widget _buildUnavailableRow(String label, String reason) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: const TextStyle(fontFamily: 'Consolas', fontSize: 9, color: UltronTheme.cleanGrey),
        ),
        Text(
          reason,
          style: const TextStyle(fontFamily: 'Consolas', fontSize: 10, color: UltronTheme.rubyRed, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }

  Widget _buildAuditLogCard(BuildContext context, ControlController controller) {
    Color statusColor;
    switch (controller.activeCommandStatus) {
      case "completed":
        statusColor = UltronTheme.neonGreen;
        break;
      case "waiting_confirmation":
        statusColor = UltronTheme.amberWarning;
        break;
      case "rejected":
      case "failed":
        statusColor = UltronTheme.rubyRed;
        break;
      case "started":
      case "sending":
        statusColor = UltronTheme.cyanAccent;
        break;
      default:
        statusColor = UltronTheme.cleanGrey;
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: UltronTheme.spaceSurface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: statusColor.withOpacity(0.3), width: 0.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                "TRANSACTION STATUS AUDIT",
                style: TextStyle(fontFamily: 'Consolas', fontSize: 10, color: UltronTheme.cleanGrey),
              ),
              Text(
                controller.activeCommandStatus.toUpperCase(),
                style: TextStyle(fontFamily: 'Consolas', fontSize: 10, fontWeight: FontWeight.bold, color: statusColor),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            controller.activeCommandMessage.isEmpty ? "No active transaction in pipeline." : controller.activeCommandMessage,
            style: const TextStyle(fontSize: 12, height: 1.4),
          ),
        ],
      ),
    );
  }

  Widget _buildButton(BuildContext context, String label, VoidCallback onPressed) {
    return ElevatedButton(
      style: ElevatedButton.styleFrom(
        padding: const EdgeInsets.symmetric(vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      onPressed: onPressed,
      child: Text(label),
    );
  }

  Widget _buildConfirmationDialogOverlay(BuildContext context, ControlController controller) {
    return Container(
      color: Colors.black.withOpacity(0.8),
      alignment: Alignment.center,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 24),
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: UltronTheme.spaceSurface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: UltronTheme.amberWarning, width: 0.5),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Icon(Icons.security_outlined, size: 50, color: UltronTheme.amberWarning),
            const SizedBox(height: 16),
            const Center(
              child: Text(
                "ULTRON REQUESTS CONFIRMATION",
                style: TextStyle(fontFamily: 'Consolas', fontSize: 12, fontWeight: FontWeight.bold, color: UltronTheme.amberWarning),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              controller.pendingConfirmation!["description"] ?? "Execute system tool?",
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),
            const Text(
              "This action will initiate automated operations on your paired laptop host.",
              style: TextStyle(fontSize: 12, color: UltronTheme.cleanGrey, height: 1.4),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            Center(
              child: Text(
                "Expires in ${controller.countdownSeconds} seconds",
                style: const TextStyle(fontFamily: 'Consolas', fontSize: 11, color: UltronTheme.rubyRed, fontWeight: FontWeight.bold),
              ),
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: UltronTheme.cleanGrey,
                      side: const BorderSide(color: UltronTheme.cleanGrey),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    onPressed: () => controller.submitDecision(false),
                    child: const Text("CANCEL"),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: UltronTheme.amberWarning,
                      foregroundColor: UltronTheme.obsidianBackground,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    onPressed: () => controller.submitDecision(true),
                    child: const Text("CONFIRM"),
                  ),
                ),
              ],
            )
          ],
        ),
      ),
    );
  }
}
