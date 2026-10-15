import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../../core/api_client.dart';
import '../../core/repository.dart';
import '../../core/status_ui.dart';

class ReportsScreen extends ConsumerWidget {
  const ReportsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final value = ref.watch(reportProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Отчёт за 24 часа'), actions: [
        IconButton(
            onPressed: () => ref.invalidate(reportProvider),
            icon: const Icon(Icons.refresh))
      ]),
      body: AsyncPanel(
        value: value,
        retry: () => ref.invalidate(reportProvider),
        data: (data) {
          final items = data['items'] as List;
          return ListView(padding: const EdgeInsets.all(16), children: [
            Text(data['note'] as String),
            const SizedBox(height: 12),
            if (items.isEmpty)
              const Card(
                  child: Padding(
                      padding: EdgeInsets.all(16),
                      child: Text('Нет наблюдений за выбранный период'))),
            for (final raw in items)
              Builder(builder: (_) {
                final item = raw as Map;
                return Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      title: Text(item['name'] as String),
                      subtitle: Text(
                          '${item['address']} · проверок: ${item['checks']} · средняя задержка: ${item['average_latency_ms'] ?? 'нет данных'} мс'),
                      trailing: Text(
                          item['observed_availability_percent'] == null
                              ? '—'
                              : '${item['observed_availability_percent']}%',
                          style: Theme.of(context).textTheme.titleMedium),
                    ));
              }),
            const SizedBox(height: 12),
            FilledButton.icon(
                onPressed: () => _shareCsv(context, ref),
                icon: const Icon(Icons.ios_share),
                label: const Text('Экспортировать CSV')),
          ]);
        },
      ),
    );
  }

  Future<void> _shareCsv(BuildContext context, WidgetRef ref) async {
    try {
      final bytes = await ref.read(repositoryProvider).availabilityCsv();
      final directory = await getApplicationDocumentsDirectory();
      final file = File(
          '${directory.path}${Platform.pathSeparator}ismn_availability.csv');
      await file.writeAsBytes(bytes, flush: true);
      await Share.shareXFiles([XFile(file.path)],
          text: 'Отчёт доступности ISMN');
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(apiErrorMessage(error))));
      }
    }
  }
}
