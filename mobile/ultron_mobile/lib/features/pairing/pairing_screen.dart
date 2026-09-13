// mobile/ultron_mobile/lib/features/pairing/pairing_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:ultron_mobile/app/theme.dart';
import 'package:ultron_mobile/features/connection/connection_controller.dart' as ultron;

class PairingScreen extends StatefulWidget {
  const PairingScreen({super.key});

  @override
  State<PairingScreen> createState() => _PairingScreenState();
}

class _PairingScreenState extends State<PairingScreen> {
  final _hostController = TextEditingController(text: "192.168.1.10:8000");
  final _codeController = TextEditingController();
  final _nameController = TextEditingController(text: "Tag's Android");

  @override
  void dispose() {
    _hostController.dispose();
    _codeController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  void _onPairPressed(BuildContext context) async {
    final host = _hostController.text.trim();
    final code = _codeController.text.trim();
    final name = _nameController.text.trim();

    if (host.isEmpty || code.isEmpty || name.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("All fields are strictly required.")),
      );
      return;
    }

    try {
      final controller = Provider.of<ultron.ConnectionController>(context, listen: false);
      await controller.pairDevice(host, code, name);
    } catch (e) {
      // Errors handled statefully by Controller error views
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UltronTheme.obsidianBackground,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Consumer<ultron.ConnectionController>(
            builder: (context, controller, child) {
              final isPairing = controller.state == ultron.ConnectionState.pairing;
              final hasError = controller.state == ultron.ConnectionState.error;

              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: 40),
                  // Logo Title Header
                  Center(
                    child: Text(
                      "ULTRON-AI",
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Center(
                    child: Text(
                      "REMOTE HUD GATEWAY INTERFACE",
                      style: TextStyle(
                        fontFamily: 'Consolas',
                        fontSize: 10,
                        color: UltronTheme.cleanGrey,
                        letterSpacing: 2.0,
                      ),
                    ),
                  ),
                  const SizedBox(height: 50),

                  // Host Laptop IP Address Input
                  const Text(
                    "LAPTOP HOST LAN IP PORT",
                    style: TextStyle(fontFamily: 'Consolas', fontSize: 11, color: UltronTheme.cleanGrey),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _hostController,
                    keyboardType: TextInputType.text,
                    style: const TextStyle(fontFamily: 'Consolas'),
                    decoration: const InputDecoration(
                      hintText: "e.g., 192.168.1.10:8000",
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Custom Device Name Input
                  const Text(
                    "CLIENT DEVICE NAME",
                    style: TextStyle(fontFamily: 'Consolas', fontSize: 11, color: UltronTheme.cleanGrey),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _nameController,
                    keyboardType: TextInputType.name,
                    style: const TextStyle(fontFamily: 'Inter'),
                    decoration: const InputDecoration(
                      hintText: "e.g., Tag's Phone",
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Temporary Pairing PIN code input
                  const Text(
                    "6-DIGIT TEMPORARY PAIRING PIN",
                    style: TextStyle(fontFamily: 'Consolas', fontSize: 11, color: UltronTheme.cleanGrey),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _codeController,
                    keyboardType: TextInputType.number,
                    maxLength: 6,
                    style: const TextStyle(
                      fontFamily: 'Consolas',
                      fontSize: 18,
                      letterSpacing: 8.0,
                      fontWeight: FontWeight.bold,
                    ),
                    decoration: const InputDecoration(
                      hintText: "XXXXXX",
                      counterText: "",
                    ),
                  ),
                  const SizedBox(height: 30),

                  // Error messages display
                  if (hasError)
                    Container(
                      margin: const EdgeInsets.only(bottom: 20),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: UltronTheme.rubyRed.withOpacity(0.1),
                        border: Border.all(color: UltronTheme.rubyRed),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        controller.errorMessage,
                        style: const TextStyle(color: UltronTheme.rubyRed, fontSize: 12),
                        textAlign: Center,
                      ),
                    ),

                  // Pairing Submit Button
                  isPairing
                      ? const Center(
                          child: CircularProgressIndicator(color: UltronTheme.cyanAccent),
                        )
                      : ElevatedButton(
                          onPressed: () => _onPairPressed(context),
                          child: const Text("PAIR AND CONNECT"),
                        ),
                  const SizedBox(height: 20),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}
