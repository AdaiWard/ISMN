import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/repository.dart';
import '../../core/status_ui.dart';

class IncidentsScreen extends ConsumerWidget {
  const IncidentsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final value = ref.watch(incidentsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Центр инцидентов'), actions: [
        IconButton(
            onPressed: () => ref.invalidate(incidentsProvider),
            icon: const Icon(Icons.refresh))
      ]),
      body: AsyncPanel(
        value: value,
        retry: () => ref.invalidate(incidentsProvider),
        data: (items) => items.isEmpty
            ? const Center(child: Text('Инцидентов нет'))
            : RefreshIndicator(
                onRefresh: () => ref.refresh(incidentsProvider.future),
                child: ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: items.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, index) {
                    final item = items[index];
                    return Card(
                        child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(children: [
                                    Expanded(
                                        child: Text(item['title'] as String,
                                            style: const TextStyle(
                                                fontWeight: FontWeight.w600))),
                                    StatusChip(item['status'] as String)
                                  ]),
                                  const SizedBox(height: 8),
                                  Text(item['explanation'] as String),
                                  const SizedBox(height: 8),
                                  Text(
                                      'Правило: ${item['rule_key']} · важность: ${item['severity']}'),
                                  if (item['status'] == 'open')
                                    Align(
                                        alignment: Alignment.centerRight,
                                        child: TextButton(
                                            onPressed: () => _ack(context, ref,
                                                item['id'] as int),
                                            child: const Text(
                                                'Принять в работу'))),
                                ])));
                  },
                ),
              ),
      ),
    );
  }

  Future<void> _ack(BuildContext context, WidgetRef ref, int id) async {
    try {
      await ref.read(repositoryProvider).acknowledge(id);
      ref.invalidate(incidentsProvider);
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(apiErrorMessage(error))));
      }
    }
  }
}
