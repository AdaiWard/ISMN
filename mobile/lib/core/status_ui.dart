import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'theme.dart';

Color statusColor(String status) => switch (status) {
      'online' || 'resolved' => success,
      'offline' || 'critical' => danger,
      'degraded' || 'warning' || 'acknowledged' => warning,
      'maintenance' => const Color(0xFF7C3AED),
      _ => const Color(0xFF66758A),
    };

String statusLabel(String status) => switch (status) {
      'online' => 'Онлайн',
      'offline' => 'Офлайн',
      'degraded' => 'Снижение качества',
      'unknown' => 'Неизвестно',
      'maintenance' => 'Обслуживание',
      'open' => 'Открыт',
      'acknowledged' => 'Принят',
      'resolved' => 'Закрыт',
      _ => status,
    };

class StatusChip extends StatelessWidget {
  const StatusChip(this.status, {super.key});
  final String status;

  @override
  Widget build(BuildContext context) {
    final color = statusColor(status);
    return Chip(
      visualDensity: VisualDensity.compact,
      label: Text(statusLabel(status)),
      side: BorderSide(color: color.withValues(alpha: .35)),
      backgroundColor: color.withValues(alpha: .1),
      labelStyle: TextStyle(color: color, fontWeight: FontWeight.w600),
    );
  }
}

class AsyncPanel<T> extends StatelessWidget {
  const AsyncPanel(
      {required this.value,
      required this.data,
      required this.retry,
      super.key});
  final AsyncValue<T> value;
  final Widget Function(T) data;
  final VoidCallback retry;

  @override
  Widget build(BuildContext context) => value.when(
        data: data,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              const Icon(Icons.cloud_off_outlined, size: 44),
              const SizedBox(height: 12),
              Text('Данные недоступны\n$error', textAlign: TextAlign.center),
              const SizedBox(height: 12),
              FilledButton.tonal(
                  onPressed: retry, child: const Text('Повторить')),
            ]),
          ),
        ),
      );
}
