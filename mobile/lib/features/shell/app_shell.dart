import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/live_events.dart';
import '../../core/repository.dart';

class AppShell extends ConsumerWidget {
  const AppShell({required this.location, required this.child, super.key});
  final String location;
  final Widget child;

  int get index {
    if (location.startsWith('/devices')) return 1;
    if (location.startsWith('/incidents')) return 2;
    if (!location.startsWith('/dashboard')) return 3;
    return 0;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.listen(liveEventsProvider, (_, next) {
      if (next.hasValue) {
        ref.invalidate(dashboardProvider);
        ref.invalidate(devicesProvider);
        ref.invalidate(incidentsProvider);
      }
    });
    return Scaffold(
      body: SafeArea(child: child),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (value) => context
            .go(['/dashboard', '/devices', '/incidents', '/more'][value]),
        destinations: const [
          NavigationDestination(
              icon: Icon(Icons.dashboard_outlined),
              selectedIcon: Icon(Icons.dashboard),
              label: 'Обзор'),
          NavigationDestination(
              icon: Icon(Icons.dns_outlined),
              selectedIcon: Icon(Icons.dns),
              label: 'Устройства'),
          NavigationDestination(
              icon: Icon(Icons.notifications_outlined),
              selectedIcon: Icon(Icons.notifications),
              label: 'Инциденты'),
          NavigationDestination(icon: Icon(Icons.more_horiz), label: 'Ещё'),
        ],
      ),
    );
  }
}
