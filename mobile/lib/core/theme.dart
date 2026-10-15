import 'package:flutter/material.dart';

const primary = Color(0xFF176BFA);
const navy = Color(0xFF16233B);
const success = Color(0xFF16805D);
const warning = Color(0xFFB7791F);
const danger = Color(0xFFC43D3D);

ThemeData buildLightTheme() => ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primary,
        primary: primary,
        surface: Colors.white,
        error: danger,
        brightness: Brightness.light,
      ),
      scaffoldBackgroundColor: const Color(0xFFF8FAFC),
      cardTheme: const CardThemeData(elevation: 0, margin: EdgeInsets.zero),
      inputDecorationTheme:
          const InputDecorationTheme(border: OutlineInputBorder()),
      navigationBarTheme:
          const NavigationBarThemeData(indicatorColor: Color(0xFFDCE9FF)),
    );

ThemeData buildDarkTheme() => ThemeData(
      useMaterial3: true,
      colorScheme:
          ColorScheme.fromSeed(seedColor: primary, brightness: Brightness.dark),
    );
