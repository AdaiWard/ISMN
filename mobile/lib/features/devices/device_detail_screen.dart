import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/api_client.dart';
import '../../core/repository.dart';
import '../../core/status_ui.dart';

class DeviceDetailScreen extends ConsumerWidget {
  const DeviceDetailScreen({required this.id, super.key});
  final int id;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final device = ref.watch(deviceProvider(id));
    final metrics = ref.watch(metricsProvider(id));
    return Scaffold(
      appBar: AppBar(title: const Text('Устройство'), actions: [
        IconButton(
            tooltip: 'Обновить',
            onPressed: () {
              ref.invalidate(deviceProvider(id));
              ref.invalidate(metricsProvider(id));
            },
            icon: const Icon(Icons.refresh)),
        PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'archive') _archive(context, ref);
            },
            itemBuilder: (_) => const [
                  PopupMenuItem(value: 'archive', child: Text('Архивировать'))
                ]),
      ]),
      body: AsyncPanel(
        value: device,
        retry: () => ref.invalidate(deviceProvider(id)),
        data: (item) => ListView(padding: const EdgeInsets.all(16), children: [
          Row(children: [
            Expanded(
                child: Text(item['name'] as String,
                    style: Theme.of(context).textTheme.headlineSmall)),
            StatusChip(item['status'] as String)
          ]),
          if (item['is_simulated'] == true) ...[
            const SizedBox(height: 12),
            Card(
              color: Theme.of(context).colorScheme.secondaryContainer,
              child: const ListTile(
                leading: Icon(Icons.science_outlined),
                title: Text('ДЕМО / СИМУЛЯЦИЯ',
                    style: TextStyle(fontWeight: FontWeight.bold)),
                subtitle: Text(
                    'Все показатели и управляющие действия виртуальные. Команды в реальную сеть не отправляются.'),
              ),
            ),
          ],
          const SizedBox(height: 8),
          Text('${item['address']} · ${item['device_type']}'),
          if (item['location'] != null)
            Text('Расположение: ${item['location']}'),
          const SizedBox(height: 16),
          Card(
              child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Наблюдение',
                            style: TextStyle(fontWeight: FontWeight.w600)),
                        const SizedBox(height: 8),
                        Text(
                            'Последняя проверка: ${_date(item['last_checked_at'])}'),
                        Text(
                            'Последний успешный ответ: ${_date(item['last_success_at'])}'),
                        Text('Профиль: ${item['monitoring_profile']}'),
                        const SizedBox(height: 8),
                        const Text(
                            'ICMP подтверждает достижимость, но не состояние CPU, RAM, питания или кабеля.'),
                      ]))),
          const SizedBox(height: 12),
          SizedBox(
              height: 220,
              child: Card(
                  child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: metrics.when(
                        loading: () =>
                            const Center(child: CircularProgressIndicator()),
                        error: (error, _) => Text('График недоступен: $error'),
                        data: (values) => values.isEmpty
                            ? const Center(
                                child: Text(
                                    'Недостаточно данных для графика задержки'))
                            : LineChart(LineChartData(
                                minY: 0,
                                gridData: const FlGridData(show: true),
                                titlesData: const FlTitlesData(
                                    topTitles: AxisTitles(
                                        sideTitles:
                                            SideTitles(showTitles: false)),
                                    rightTitles: AxisTitles(
                                        sideTitles:
                                            SideTitles(showTitles: false))),
                                lineBarsData: [
                                  LineChartBarData(
                                      isCurved: true,
                                      color:
                                          Theme.of(context).colorScheme.primary,
                                      dotData: const FlDotData(show: false),
                                      spots: [
                                        for (var i = 0; i < values.length; i++)
                                          FlSpot(
                                              i.toDouble(),
                                              (values[i]['value'] as num)
                                                  .toDouble())
                                      ])
                                ],
                              )),
                      )))),
          const SizedBox(height: 12),
          if (item['is_simulated'] == true) ...[
            _DemoControls(deviceId: id),
            const SizedBox(height: 12),
          ],
          FilledButton.icon(
              onPressed: () => _check(context, ref),
              icon: const Icon(Icons.play_arrow),
              label: const Text('Запустить проверку сейчас')),
        ]),
      ),
    );
  }

  String _date(dynamic value) => value == null
      ? 'нет данных'
      : DateFormat('dd.MM.yyyy HH:mm:ss')
          .format(DateTime.parse(value as String).toLocal());

  Future<void> _check(BuildContext context, WidgetRef ref) async {
    try {
      final result = await ref.read(repositoryProvider).checkDevice(id);
      ref.invalidate(deviceProvider(id));
      ref.invalidate(metricsProvider(id));
      if (context.mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(result['detail'] as String)));
      }
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(apiErrorMessage(error))));
      }
    }
  }

  Future<void> _archive(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
              title: const Text('Архивировать устройство?'),
              content: const Text(
                  'Мониторинг будет остановлен, история сохранится.'),
              actions: [
                TextButton(
                    onPressed: () => Navigator.pop(context, false),
                    child: const Text('Отмена')),
                FilledButton(
                    onPressed: () => Navigator.pop(context, true),
                    child: const Text('Архивировать'))
              ],
            ));
    if (confirmed != true || !context.mounted) return;
    try {
      await ref.read(repositoryProvider).archiveDevice(id);
      ref.invalidate(devicesProvider);
      if (context.mounted) context.go('/devices');
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(apiErrorMessage(error))));
      }
    }
  }
}

class _DemoControls extends ConsumerWidget {
  const _DemoControls({required this.deviceId});

  final int deviceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final interfaces = ref.watch(deviceInterfacesProvider(deviceId));
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Демо-управление',
                style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            const Text(
                'Действия требуют подтверждения и сохраняются в журнале аудита.'),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilledButton.tonalIcon(
                  onPressed: () => _run(context, ref, 'retry_check',
                      'Запустить виртуальную диагностику?'),
                  icon: const Icon(Icons.monitor_heart_outlined),
                  label: const Text('Диагностика'),
                ),
                OutlinedButton.icon(
                  onPressed: () => _run(context, ref, 'reboot_device',
                      'Перезагрузить виртуальное устройство?'),
                  icon: const Icon(Icons.restart_alt),
                  label: const Text('Перезагрузить'),
                ),
              ],
            ),
            const Divider(height: 28),
            Text('Интерфейсы', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            interfaces.when(
              loading: () => const Center(
                  child: Padding(
                      padding: EdgeInsets.all(12),
                      child: CircularProgressIndicator())),
              error: (error, _) => Text(
                  'Не удалось загрузить интерфейсы: ${apiErrorMessage(error)}'),
              data: (items) => Column(children: [
                for (final item in items) _interfaceTile(context, ref, item)
              ]),
            ),
          ],
        ),
      ),
    );
  }

  Widget _interfaceTile(BuildContext context, WidgetRef ref, Json item) {
    final protected = item['is_uplink'] == true ||
        item['is_trunk'] == true ||
        item['remediation_allowed'] != true;
    final isUp = item['oper_status'] == 'up';
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Icon(isUp ? Icons.lan_outlined : Icons.link_off,
          color: isUp ? Colors.green : Theme.of(context).colorScheme.error),
      title: Text(item['name'] as String),
      subtitle: Text(protected
          ? 'Защищённый UPLINK — управление запрещено'
          : (isUp ? 'Включён' : 'Отключён')),
      trailing: protected
          ? const Icon(Icons.lock_outline)
          : PopupMenuButton<String>(
              tooltip: 'Управление интерфейсом',
              onSelected: (action) => _run(
                context,
                ref,
                action,
                '${_actionLabel(action)} ${item['name']}?',
                interfaceId: item['id'] as int,
              ),
              itemBuilder: (_) => [
                PopupMenuItem(
                    value: isUp ? 'disable_interface' : 'enable_interface',
                    child: Text(isUp ? 'Отключить' : 'Включить')),
                const PopupMenuItem(
                    value: 'restart_interface', child: Text('Перезапустить')),
              ],
            ),
    );
  }

  String _actionLabel(String action) => switch (action) {
        'enable_interface' => 'Включить',
        'disable_interface' => 'Отключить',
        'restart_interface' => 'Перезапустить',
        _ => 'Выполнить действие для',
      };

  Future<void> _run(
      BuildContext context, WidgetRef ref, String action, String question,
      {int? interfaceId}) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Подтверждение демо-действия'),
        content: Text(
            '$question\n\nЭто симуляция: реальная сетевая команда не отправляется.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Отмена')),
          FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Подтвердить')),
        ],
      ),
    );
    if (confirmed != true || !context.mounted) return;
    try {
      final result = await ref
          .read(repositoryProvider)
          .runDemoAction(deviceId, action, interfaceId: interfaceId);
      ref.invalidate(deviceProvider(deviceId));
      ref.invalidate(deviceInterfacesProvider(deviceId));
      ref.invalidate(metricsProvider(deviceId));
      if (context.mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(result['detail'] as String)));
      }
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(apiErrorMessage(error))));
      }
    }
  }
}
