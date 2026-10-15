import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/repository.dart';
import '../../core/status_ui.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final value = ref.watch(dashboardProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Обзор сети'), actions: [
        IconButton(
            tooltip: 'Обновить',
            onPressed: () => ref.invalidate(dashboardProvider),
            icon: const Icon(Icons.refresh))
      ]),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(dashboardProvider.future),
        child: AsyncPanel(
          value: value,
          retry: () => ref.invalidate(dashboardProvider),
          data: (data) {
            final counts =
                Map<String, dynamic>.from(data['status_counts'] as Map);
            return ListView(padding: const EdgeInsets.all(16), children: [
              Wrap(spacing: 12, runSpacing: 12, children: [
                _Metric(
                    title: 'Всего',
                    value: '${data['total_devices']}',
                    icon: Icons.hub_outlined),
                _Metric(
                    title: 'Онлайн',
                    value: '${counts['online']}',
                    icon: Icons.check_circle_outline,
                    color: statusColor('online')),
                _Metric(
                    title: 'Офлайн',
                    value: '${counts['offline']}',
                    icon: Icons.cancel_outlined,
                    color: statusColor('offline')),
                _Metric(
                    title: 'Проблемы',
                    value: '${counts['degraded']}',
                    icon: Icons.warning_amber,
                    color: statusColor('degraded')),
              ]),
              const SizedBox(height: 16),
              Card(
                  child: ListTile(
                      leading: const Icon(Icons.notifications_active_outlined),
                      title: const Text('Активные инциденты'),
                      trailing: Text('${data['active_incidents']}',
                          style: Theme.of(context).textTheme.headlineSmall))),
              const SizedBox(height: 12),
              Card(
                  child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Источник данных',
                                style: TextStyle(fontWeight: FontWeight.w600)),
                            const SizedBox(height: 6),
                            const Text(
                                'Серверная SQLite. Показатели не генерируются мобильным приложением.'),
                            const SizedBox(height: 6),
                            Text(
                                'Обновлено: ${DateFormat('dd.MM.yyyy HH:mm:ss').format(DateTime.parse(data['generated_at'] as String).toLocal())}'),
                          ]))),
            ]);
          },
        ),
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric(
      {required this.title,
      required this.value,
      required this.icon,
      this.color});
  final String title;
  final String value;
  final IconData icon;
  final Color? color;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: (MediaQuery.sizeOf(context).width - 44) / 2,
        child: Card(
            child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(children: [
                  Icon(icon, color: color),
                  const SizedBox(width: 12),
                  Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(value,
                            style: Theme.of(context).textTheme.headlineSmall),
                        Text(title)
                      ]),
                ]))),
      );
}
