// mobile/ultron_mobile/lib/app/app.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:ultron_mobile/app/theme.dart';
import 'package:ultron_mobile/features/connection/connection_controller.dart' as ultron;
import 'package:ultron_mobile/features/pairing/pairing_screen.dart';
import 'package:ultron_mobile/features/home/home_screen.dart';

class UltronApp extends StatelessWidget {
  const UltronApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ULTRON HUD',
      theme: UltronTheme.darkTheme,
      debugShowCheckedModeBanner: false,
      home: const MainGatekeeper(),
    );
  }
}

class MainGatekeeper extends StatelessWidget {
  const MainGatekeeper({super.key});

  @override
  Widget build(BuildContext context) {
    // Listens statefully to active pairing connection states to toggle routing
    return Consumer<ultron.ConnectionController>(
      builder: (context, controller, child) {
        if (!controller.isPaired) {
          return const PairingScreen();
        }
        return const HomeScreen();
      },
    );
  }
}
