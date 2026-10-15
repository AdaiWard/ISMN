import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth_state.dart';
import '../../core/config_store.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _server = TextEditingController();
  final _username = TextEditingController();
  final _password = TextEditingController();
  bool _tested = false;
  String? _connectionMessage;

  @override
  void initState() {
    super.initState();
    Future.microtask(() => _server.text =
        ref.read(serverConfigProvider).valueOrNull ??
            ServerConfigNotifier.fallback);
  }

  @override
  void dispose() {
    _server.dispose();
    _username.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _testServer() async {
    setState(() => _connectionMessage = 'Проверка…');
    try {
      await ref.read(serverConfigProvider.notifier).save(_server.text);
      final url = ref.read(serverConfigProvider).requireValue;
      final response =
          await Dio(BaseOptions(connectTimeout: const Duration(seconds: 4)))
              .get('$url/health/live');
      setState(() {
        _tested = response.statusCode == 200;
        _connectionMessage =
            _tested ? 'Сервер ISMN доступен' : 'Неожиданный ответ сервера';
      });
    } catch (_) {
      setState(() {
        _tested = false;
        _connectionMessage =
            'Сервер недоступен. Для эмулятора используйте 10.0.2.2, для телефона — LAN IP компьютера.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 430),
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Image.asset('assets/images/ismn_logo.png',
                      height: 150,
                      fit: BoxFit.contain,
                      semanticLabel: 'Логотип ISMN'),
                  const SizedBox(height: 16),
                  Text('Сетевой центр ISMN',
                      style: Theme.of(context).textTheme.headlineSmall,
                      textAlign: TextAlign.center),
                  const SizedBox(height: 8),
                  Text(
                      'Мониторинг выполняется сервером, даже когда приложение закрыто.',
                      style: Theme.of(context).textTheme.bodyMedium,
                      textAlign: TextAlign.center),
                  const SizedBox(height: 24),
                  TextField(
                      controller: _server,
                      keyboardType: TextInputType.url,
                      decoration: const InputDecoration(
                          labelText: 'Адрес сервера',
                          hintText: 'http://192.168.1.100:8000',
                          prefixIcon: Icon(Icons.lan_outlined))),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                      onPressed: _testServer,
                      icon: const Icon(Icons.wifi_find),
                      label: const Text('Проверить соединение')),
                  if (_connectionMessage != null)
                    Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: Text(_connectionMessage!,
                            textAlign: TextAlign.center)),
                  const SizedBox(height: 16),
                  TextField(
                      controller: _username,
                      autocorrect: false,
                      decoration: const InputDecoration(
                          labelText: 'Пользователь',
                          prefixIcon: Icon(Icons.person_outline))),
                  const SizedBox(height: 12),
                  TextField(
                      controller: _password,
                      obscureText: true,
                      onSubmitted: (_) => _login(),
                      decoration: const InputDecoration(
                          labelText: 'Пароль',
                          prefixIcon: Icon(Icons.lock_outline))),
                  if (auth.error != null)
                    Padding(
                        padding: const EdgeInsets.only(top: 12),
                        child: Text(auth.error!,
                            style: TextStyle(
                                color: Theme.of(context).colorScheme.error))),
                  const SizedBox(height: 16),
                  FilledButton(
                      onPressed: auth.loading ? null : _login,
                      child: auth.loading
                          ? const SizedBox.square(
                              dimension: 20,
                              child: CircularProgressIndicator(strokeWidth: 2))
                          : const Text('Войти')),
                  const SizedBox(height: 12),
                  const Text(
                      'HTTP допустим только в изолированной учебной LAN и debug-сборке. Для рабочей сети настройте HTTPS.',
                      textAlign: TextAlign.center),
                ]),
          ),
        ),
      ),
    );
  }

  Future<void> _login() async {
    if (!_tested) await _testServer();
    if (!_tested) return;
    await ref
        .read(authProvider.notifier)
        .signIn(_username.text.trim(), _password.text);
  }
}
