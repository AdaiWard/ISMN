import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('offline state can be rendered accessibly', (tester) async {
    await tester.pumpWidget(const MaterialApp(
        home: Scaffold(
            body: Center(
                child: Text('Сервер недоступен. Проверьте адрес и сеть.')))));
    expect(find.textContaining('Сервер недоступен'), findsOneWidget);
  });

  testWidgets('navigation labels are present', (tester) async {
    await tester.pumpWidget(MaterialApp(
        home: Scaffold(
            bottomNavigationBar: NavigationBar(destinations: const [
      NavigationDestination(icon: Icon(Icons.dashboard), label: 'Обзор'),
      NavigationDestination(icon: Icon(Icons.dns), label: 'Устройства'),
    ]))));
    expect(find.text('Обзор'), findsOneWidget);
    expect(find.text('Устройства'), findsOneWidget);
  });
}
