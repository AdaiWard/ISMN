import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/repository.dart';
import '../../core/status_ui.dart';

class AutomationScreen extends ConsumerWidget {
  const AutomationScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final value = ref.watch(automationProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Автоматизация')),
      body: AsyncPanel(
        value: value,
        retry: () => ref.invalidate(automationProvider),
        data: (data) {
          final paused = data.status['paused'] == true;
          return ListView(padding: const EdgeInsets.all(16), children: [
            Card(
                color: paused
                    ? Theme.of(context).colorScheme.errorContainer
                    : null,
                child: SwitchListTile(
                  value: paused,
                  title: Text(paused
                      ? 'Аварийная пауза включена'
                      : 'Автоматизация разрешена'),
                  subtitle: const Text(
                      'По умолчанию правила работают в DRY-RUN. Сетевые команды не выполняются без отдельного одобрения.'),
                  onChanged: (value) => _pause(context, ref, value),
                )),
            const SizedBox(height: 16),
            Text('Правила', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            if (data.rules.isEmpty)
              const Card(
                  child: Padding(
                      padding: EdgeInsets.all(16),
                      child: Text(
                          'Правила ещё не созданы. Создайте их через документированный API администратора.'))),
            for (final rule in data.rules)
              Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  leading: const Icon(Icons.rule_outlined),
                  title: Text(rule['name'] as String),
                  subtitle:
                      Text('${rule['trigger_key']} → ${rule['action_type']}'),
                  trailing:
                      Chip(label: Text((rule['mode'] as String).toUpperCase())),
                ),
              ),
          ]);
        },
      ),
    );
  }

  Future<void> _pause(BuildContext context, WidgetRef ref, bool paused) async {
    try {
      await ref.read(repositoryProvider).setAutomationPaused(paused);
      ref.invalidate(automationProvider);
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(apiErrorMessage(error))));
      }
    }
  }
}
