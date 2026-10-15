import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/repository.dart';
import '../../core/status_ui.dart';

class TopologyScreen extends ConsumerWidget {
  const TopologyScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final value = ref.watch(topologyProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Топология')),
      body: AsyncPanel(
        value: value,
        retry: () => ref.invalidate(topologyProvider),
        data: (data) {
          final nodes = data['nodes'] as List;
          final links = data['links'] as List;
          return ListView(padding: const EdgeInsets.all(16), children: [
            Card(
                color: Theme.of(context).colorScheme.secondaryContainer,
                child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text(data['notice'] as String))),
            const SizedBox(height: 16),
            Text('Узлы', style: Theme.of(context).textTheme.titleLarge),
            for (final raw in nodes)
              Builder(builder: (_) {
                final node = raw as Map;
                return ListTile(
                    leading: Icon(Icons.circle,
                        size: 14, color: statusColor(node['status'] as String)),
                    title: Text(node['name'] as String),
                    subtitle: Text(node['type'] as String));
              }),
            const Divider(),
            Text('Ручные связи (${links.length})',
                style: Theme.of(context).textTheme.titleLarge),
            if (links.isEmpty)
              const Padding(
                  padding: EdgeInsets.symmetric(vertical: 16),
                  child: Text('Связи пока не заданы')),
            for (final raw in links)
              Builder(builder: (_) {
                final link = raw as Map;
                return ListTile(
                    leading: const Icon(Icons.linear_scale),
                    title: Text('${link['source']} ↔ ${link['target']}'),
                    subtitle: Text(link['label'] as String? ?? 'Ручная связь'));
              }),
          ]);
        },
      ),
    );
  }
}
