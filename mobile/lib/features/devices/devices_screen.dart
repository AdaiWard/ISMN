import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/repository.dart';
import '../../core/status_ui.dart';

class DevicesScreen extends ConsumerWidget {
  const DevicesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final value = ref.watch(devicesProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Устройства'), actions: [
        IconButton(
            tooltip: 'Обновить',
            onPressed: () => ref.invalidate(devicesProvider),
            icon: const Icon(Icons.refresh))
      ]),
      floatingActionButton: FloatingActionButton.extended(
          onPressed: () => context.push('/devices/add'),
          icon: const Icon(Icons.add),
          label: const Text('Добавить')),
      body: AsyncPanel(
        value: value,
        retry: () => ref.invalidate(devicesProvider),
        data: (items) => items.isEmpty
            ? const Center(
                child: Padding(
                    padding: EdgeInsets.all(32),
                    child: Text(
                        'Нет зарегистрированных устройств. Добавьте только принадлежащее вам устройство из разрешённой сети.',
                        textAlign: TextAlign.center)))
            : RefreshIndicator(
                onRefresh: () => ref.refresh(devicesProvider.future),
                child: ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
                  itemCount: items.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, index) {
                    final item = items[index];
                    return Card(
                        child: ListTile(
                      onTap: () => context.push('/devices/${item['id']}'),
                      leading: Icon(_icon(item['device_type'] as String)),
                      title: Text(item['name'] as String),
                      subtitle: Text(item['is_simulated'] == true
                          ? 'ДЕМО / СИМУЛЯЦИЯ · ${item['device_type']}'
                          : '${item['address']} · ${item['monitoring_profile']}'),
                      trailing: StatusChip(item['status'] as String),
                    ));
                  },
                ),
              ),
      ),
    );
  }

  IconData _icon(String type) => switch (type) {
        'router' => Icons.router_outlined,
        'switch' => Icons.hub_outlined,
        'server' => Icons.dns_outlined,
        'printer' => Icons.print_outlined,
        'access_point' => Icons.wifi_outlined,
        _ => Icons.computer_outlined,
      };
}
