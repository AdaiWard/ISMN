import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/login_screen.dart';
import '../features/automation/automation_screen.dart';
import '../features/dashboard/dashboard_screen.dart';
import '../features/devices/add_device_screen.dart';
import '../features/devices/device_detail_screen.dart';
import '../features/devices/devices_screen.dart';
import '../features/incidents/incidents_screen.dart';
import '../features/more/more_screen.dart';
import '../features/reports/reports_screen.dart';
import '../features/settings/settings_screen.dart';
import '../features/topology/topology_screen.dart';
import '../features/users/users_screen.dart';
import '../features/shell/app_shell.dart';
import 'auth_state.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final auth = ref.watch(authProvider);
  return GoRouter(
    initialLocation: '/dashboard',
    redirect: (_, state) {
      if (auth.loading) return null;
      final loggingIn = state.matchedLocation == '/login';
      if (!auth.authenticated && !loggingIn) return '/login';
      if (auth.authenticated && loggingIn) return '/dashboard';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      ShellRoute(
        builder: (_, state, child) =>
            AppShell(location: state.uri.path, child: child),
        routes: [
          GoRoute(
              path: '/dashboard', builder: (_, __) => const DashboardScreen()),
          GoRoute(path: '/devices', builder: (_, __) => const DevicesScreen()),
          GoRoute(
              path: '/devices/add',
              builder: (_, __) => const AddDeviceScreen()),
          GoRoute(
              path: '/devices/:id',
              builder: (_, state) => DeviceDetailScreen(
                  id: int.parse(state.pathParameters['id']!))),
          GoRoute(
              path: '/incidents', builder: (_, __) => const IncidentsScreen()),
          GoRoute(path: '/more', builder: (_, __) => const MoreScreen()),
          GoRoute(
              path: '/automation',
              builder: (_, __) => const AutomationScreen()),
          GoRoute(path: '/reports', builder: (_, __) => const ReportsScreen()),
          GoRoute(
              path: '/topology', builder: (_, __) => const TopologyScreen()),
          GoRoute(path: '/users', builder: (_, __) => const UsersScreen()),
          GoRoute(
              path: '/settings', builder: (_, __) => const SettingsScreen()),
        ],
      ),
    ],
  );
});
