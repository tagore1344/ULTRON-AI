// mobile/ultron_mobile/lib/app/app.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:ultron_mobile/app/theme.dart';
import 'package:ultron_mobile/features/connection/connection_controller.dart' as ultron;
import 'package:ultron_mobile/features/pairing/pairing_screen.dart';
import 'package:ultron_mobile/features/home/home_screen.dart';
import 'package:ultron_mobile/features/chat/chat_screen.dart';
import 'package:ultron_mobile/features/control/control_screen.dart';

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
    return Consumer<ultron.ConnectionController>(
      builder: (context, controller, child) {
        if (!controller.isPaired) {
          return const PairingScreen();
        }
        return const NavigationScaffold();
      },
    );
  }
}

class NavigationScaffold extends StatefulWidget {
  const NavigationScaffold({super.key});

  @override
  State<NavigationScaffold> createState() => _NavigationScaffoldState();
}

class _NavigationScaffoldState extends State<NavigationScaffold> {
  int _currentIndex = 0;

  final List<Widget> _screens = [
    const HomeScreen(),
    const ChatScreen(),
    const ControlScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UltronTheme.obsidianBackground,
      body: _screens[_currentIndex],
      bottomNavigationBar: Theme(
        data: Theme.of(context).copyWith(
          canvasColor: UltronTheme.spaceSurface,
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: (index) {
            setState(() {
              _currentIndex = index;
            });
          },
          selectedItemColor: UltronTheme.cyanAccent,
          unselectedItemColor: UltronTheme.cleanGrey,
          showUnselectedLabels: true,
          type: BottomNavigationBarType.fixed,
          selectedLabelStyle: const TextStyle(fontFamily: 'Consolas', fontSize: 10, fontWeight: FontWeight.bold),
          unselectedLabelStyle: const TextStyle(fontFamily: 'Consolas', fontSize: 10),
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.home_outlined),
              activeIcon: Icon(Icons.home, color: UltronTheme.cyanAccent),
              label: "HOME",
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.chat_bubble_outline),
              activeIcon: Icon(Icons.chat_bubble, color: UltronTheme.cyanAccent),
              label: "CHAT",
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.tune_outlined),
              activeIcon: Icon(Icons.tune, color: UltronTheme.cyanAccent),
              label: "CONTROL",
            ),
          ],
        ),
      ),
    );
  }
}
