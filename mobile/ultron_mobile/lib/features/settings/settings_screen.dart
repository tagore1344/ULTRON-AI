// mobile/ultron_mobile/lib/features/settings/settings_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:ultron_mobile/app/theme.dart';
import 'package:ultron_mobile/features/connection/connection_controller.dart' as ultron;

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  void _onUnpairPressed(BuildContext context, ultron.ConnectionController controller) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: UltronTheme.spaceSurface,
        title: const Text("UNPAIR DEVICE?", style: TextStyle(fontFamily: 'Consolas', color: Colors.white)),
        content: const Text("This will disconnect from ULTRON and wipe all secure session access tokens locally."),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text("CANCEL", style: TextStyle(color: UltronTheme.cleanGrey)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: UltronTheme.rubyRed, foregroundColor: Colors.white),
            onPressed: () => Navigator.pop(context, true),
            child: const Text("UNPAIR"),
          ),
        ],
      ),
    );

    if (confirm == true) {
      await controller.unpairDevice();
      Navigator.pop(context); // Close Settings and returns to pairing screen
    }
  }

  @override
  Widget build(BuildContext context) {
    final controller = Provider.of<ultron.ConnectionController>(context, listen: false);

    return Scaffold(
      backgroundColor: UltronTheme.obsidianBackground,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text(
          "SYSTEM CONFIG",
          style: TextStyle(fontFamily: 'Consolas', fontSize: 16, fontWeight: FontWeight.bold),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                "GATEWAY PROPERTIES",
                style: TextStyle(fontFamily: 'Consolas', fontSize: 11, color: UltronTheme.cleanGrey),
              ),
              const SizedBox(height: 12),
              _buildConfigRow("SERVER HOST", "http://${controller.config.host}:${controller.config.port}"),
              _buildConfigRow("DEVICE ID", controller.isPaired ? "android_${controller.wsService.config.deviceName.hashCode.abs().toRadixString(16)}" : "UNPAIRED"),
              _buildConfigRow("DEVICE NAME", controller.pairedDeviceName ?? "Android"),
              _buildConfigRow("WS HANDSHAKE", "Single-Use 15s Ticket"),
              const SizedBox(height: 30),

              const Spacer(),

              // Unpair / Disconnect action trigger
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: UltronTheme.rubyRed.withOpacity(0.1),
                  foregroundColor: UltronTheme.rubyRed,
                  side: const BorderSide(color: UltronTheme.rubyRed, width: 0.5),
                ),
                onPressed: () => _onUnpairPressed(context, controller),
                child: const Text("UNPAIR DEVICE"),
              ),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildConfigRow(String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: UltronTheme.spaceSurface,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(fontFamily: 'Consolas', fontSize: 11, color: UltronTheme.cleanGrey),
          ),
          Text(
            value,
            style: const TextStyle(fontFamily: 'Consolas', fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
          ),
        ],
      ),
    );
  }
}
