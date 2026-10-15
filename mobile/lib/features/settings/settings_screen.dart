import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth_state.dart';
import '../../core/config_store.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  final _server = TextEditingController();
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    Future.microtask(() => setState(() => _server.text =
        ref.read(serverConfigProvider).valueOrNull ??
            ServerConfigNotifier.fallback));
  }

  @override
  void dispose() {
    _server.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Настройки')),
        body: ListView(padding: const EdgeInsets.all(16), children: [
          Text('Сервер API', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          TextField(
              controller: _server,
              keyboardType: TextInputType.url,
              decoration: const InputDecoration(
                  labelText: 'URL', hintText: 'https://ismn.local')),
          const SizedBox(height: 8),
          FilledButton.tonal(
              onPressed: _busy ? null : _saveAndTest,
              child: const Text('Сохранить и проверить')),
          const SizedBox(height: 16),
          const Card(
              child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Text(
                      'Телефон и сервер должны находиться в доверенной LAN. Для физического телефона localhost неверен — используйте LAN IP компьютера. В production включите TLS через reverse proxy и ограничьте Windows Firewall.'))),
          const SizedBox(height: 24),
          OutlinedButton.icon(
              onPressed: () => ref.read(authProvider.notifier).signOut(),
              icon: const Icon(Icons.logout),
              label: const Text('Выйти')),
        ]),
      );

  Future<void> _saveAndTest() async {
    setState(() => _busy = true);
    try {
      await ref.read(serverConfigProvider.notifier).save(_server.text);
      final url = ref.read(serverConfigProvider).requireValue;
      await Dio(BaseOptions(connectTimeout: const Duration(seconds: 4)))
          .get('$url/health/live');
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('Сервер доступен')));
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Соединение не установлено: $error')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}
