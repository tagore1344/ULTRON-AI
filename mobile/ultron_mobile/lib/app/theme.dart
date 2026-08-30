// mobile/ultron_mobile/lib/app/theme.dart
import 'package:flutter/material.dart';

class UltronTheme {
  static const Color obsidianBackground = Color(0xFF0A0F19);
  static const Color spaceSurface = Color(0xFF141D2E);
  static const Color cyanAccent = Color(0xFF00D4FF);
  static const Color rubyRed = Color(0xFFFF0055);
  static const Color neonGreen = Color(0xFF00FFAA);
  static const Color amberWarning = Color(0xFFFFB000);
  static const Color cleanGrey = Color(0xFF888899);

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      primaryColor: cyanAccent,
      scaffoldBackgroundColor: obsidianBackground,
      cardColor: spaceSurface,
      useMaterial3: true,
      colorScheme: const ColorScheme.dark(
        primary: cyanAccent,
        surface: spaceSurface,
        onSurface: Colors.white,
        error: rubyRed,
      ),
      textTheme: const TextTheme(
        headlineMedium: TextStyle(
          fontFamily: 'Consolas',
          fontSize: 22,
          fontWeight: FontWeight.bold,
          letterSpacing: 2.0,
          color: cyanAccent,
        ),
        bodyMedium: TextStyle(
          fontFamily: 'Inter',
          fontSize: 14,
          color: Colors.white,
        ),
        labelSmall: TextStyle(
          fontFamily: 'Consolas',
          fontSize: 11,
          color: cleanGrey,
          letterSpacing: 1.0,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: spaceSurface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: cleanGrey),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: cleanGrey.withOpacity(0.4)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: cyanAccent),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          foregroundColor: obsidianBackground,
          backgroundColor: cyanAccent,
          textStyle: const TextStyle(
            fontFamily: 'Consolas',
            fontWeight: FontWeight.bold,
            letterSpacing: 1.5,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
        ),
      ),
    );
  }
}
