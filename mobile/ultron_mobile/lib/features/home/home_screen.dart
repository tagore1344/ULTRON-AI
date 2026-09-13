// mobile/ultron_mobile/lib/features/home/home_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:ultron_mobile/app/theme.dart';
import 'package:ultron_mobile/features/connection/connection_controller.dart' as ultron;
import 'package:ultron_mobile/features/settings/settings_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UltronTheme.obsidianBackground,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text(
          "ULTRON HUD",
          style: TextStyle(fontFamily: 'Consolas', fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 1.5),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings, color: UltronTheme.cyanAccent),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const SettingsScreen()),
              );
            },
          )
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 12.0),
          child: Consumer<ultron.ConnectionController>(
            builder: (context, controller, child) {
              final isConnected = controller.state == ultron.ConnectionState.connected;

              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // --- HEADER STATUS ROW ---
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: UltronTheme.spaceSurface,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: isConnected ? UltronTheme.cyanAccent : UltronTheme.rubyRed,
                        width: 0.5,
                      ),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              "LAPTOP CONNECTION",
                              style: Theme.of(context).textTheme.labelSmall,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              isConnected ? "ONLINE" : "OFFLINE",
                              style: TextStyle(
                                fontFamily: 'Consolas',
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                                color: isConnected ? UltronTheme.cyanAccent : UltronTheme.rubyRed,
                              ),
                            )
                          ],
                        ),
                        // Connection Diagnostic Indicator
                        _buildStatusIndicator(context, controller.state),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),

                  // --- TELEMETRY GAUGES PLACEHOLDERS ---
                  const Text(
                    "LAPTOP TELEMETRY SYSTEM",
                    style: TextStyle(fontFamily: 'Consolas', fontSize: 11, color: UltronTheme.cleanGrey),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(child: _buildMetricCard(context, "CPU", isConnected ? "24%" : "0%")),
                      const SizedBox(width: 12),
                      Expanded(child: _buildMetricCard(context, "RAM", isConnected ? "58%" : "0%")),
                      const SizedBox(width: 12),
                      Expanded(child: _buildMetricCard(context, "GPU", isConnected ? "31%" : "0%")),
                    ],
                  ),
                  const SizedBox(height: 30),

                  // --- MAIN HUD TEXT ---
                  Expanded(
                    child: Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.mic_none_outlined,
                            size: 80,
                            color: isConnected ? UltronTheme.cyanAccent : UltronTheme.cleanGrey,
                          ),
                          const SizedBox(height: 16),
                          Text(
                            isConnected ? "ULTRON READY" : "ULTRON STANDBY",
                            style: const TextStyle(
                              fontFamily: 'Consolas',
                              fontSize: 16,
                              letterSpacing: 2.0,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            isConnected ? '"What can I help you with, sir?"' : "Waiting for laptop connection...",
                            style: const TextStyle(
                              fontFamily: 'Inter',
                              color: UltronTheme.cleanGrey,
                              fontStyle: FontStyle.italic,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),

                  // --- QUICK ACTIONS ROW ---
                  const Text(
                    "QUICK ACTIONS",
                    style: TextStyle(fontFamily: 'Consolas', fontSize: 11, color: UltronTheme.cleanGrey),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(child: _buildActionButton(context, Icons.language, "BROWSER", isConnected)),
                      const SizedBox(width: 12),
                      Expanded(child: _buildActionButton(context, Icons.music_note, "MUSIC", isConnected)),
                      const SizedBox(width: 12),
                      Expanded(child: _buildActionButton(context, Icons.camera_alt, "CAPTURE", isConnected)),
                    ],
                  ),
                  const SizedBox(height: 10),
                ],
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _buildStatusIndicator(BuildContext context, ultron.ConnectionState state) {
    Color color;
    String label;

    switch (state) {
      case ultron.ConnectionState.connected:
        color = UltronTheme.neonGreen;
        label = "CONNECTED";
        break;
      case ultron.ConnectionState.connecting:
        color = UltronTheme.amberWarning;
        label = "CONNECTING";
        break;
      case ultron.ConnectionState.reconnecting:
        color = UltronTheme.amberWarning;
        label = "RECONNECTING";
        break;
      case ultron.ConnectionState.error:
        color = UltronTheme.rubyRed;
        label = "CONNECTION ERROR";
        break;
      case ultron.ConnectionState.revoked:
        color = UltronTheme.rubyRed;
        label = "REVOKED";
        break;
      default:
        color = UltronTheme.cleanGrey;
        label = "DISCONNECTED";
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color, width: 0.5),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 8),
          Text(
            label,
            style: TextStyle(fontFamily: 'Consolas', fontSize: 10, fontWeight: FontWeight.bold, color: color),
          ),
        ],
      ),
    );
  }

  Widget _buildMetricCard(BuildContext context, String label, String value) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: UltronTheme.spaceSurface,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(fontFamily: 'Consolas', fontSize: 11, color: UltronTheme.cleanGrey),
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: const TextStyle(fontFamily: 'Consolas', fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
          ),
        ],
      ),
    );
  }

  Widget _buildActionButton(BuildContext context, IconData icon, String label, bool active) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 16),
      decoration: BoxDecoration(
        color: active ? UltronTheme.spaceSurface : UltronTheme.spaceSurface.withOpacity(0.3),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: active ? UltronTheme.cyanAccent.withOpacity(0.2) : Colors.transparent),
      ),
      child: Column(
        children: [
          Icon(icon, color: active ? UltronTheme.cyanAccent : UltronTheme.cleanGrey),
          const SizedBox(height: 8),
          Text(
            label,
            style: TextStyle(fontFamily: 'Consolas', fontSize: 10, fontWeight: FontWeight.bold, color: active ? Colors.white : UltronTheme.cleanGrey),
          ),
        ],
      ),
    );
  }
}
