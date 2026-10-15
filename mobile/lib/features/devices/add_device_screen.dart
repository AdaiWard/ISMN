import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/repository.dart';

class AddDeviceScreen extends ConsumerStatefulWidget {
  const AddDeviceScreen({super.key});

  @override
  ConsumerState<AddDeviceScreen> createState() => _AddDeviceScreenState();
}

class _AddDeviceScreenState extends ConsumerState<AddDeviceScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _address = TextEditingController();
  final _location = TextEditingController();
  String _type = 'other';
  String _profile = 'icmp';
  bool _isSimulated = false;
  bool _busy = false;
  String? _testResult;

  @override
  void dispose() {
    _name.dispose();
    _address.dispose();
    _location.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Добавить устройство')),
        body: Form(
          key: _form,
          child: ListView(padding: const EdgeInsets.all(16), children: [
            Card(
              color: _isSimulated
                  ? Theme.of(context).colorScheme.secondaryContainer
                  : null,
              child: SwitchListTile(
                value: _isSimulated,
                title: const Text('Демо-устройство'),
                subtitle: const Text(
                    'Безопасная симуляция мониторинга и управления без команд реальному оборудованию.'),
                secondary: const Icon(Icons.science_outlined),
                onChanged: _busy
                    ? null
                    : (value) => setState(() {
                          _isSimulated = value;
                          if (value) {
                            _address.text = 'demo';
                            _profile = 'test_agent';
                            if (_type == 'other') _type = 'switch';
                          } else if (_address.text == 'demo') {
                            _address.clear();
                            _profile = 'icmp';
                          }
                        }),
              ),
            ),
            const SizedBox(height: 12),
            Text('Регистрируйте только устройства вашей административной зоны.',
                style: Theme.of(context).textTheme.bodyMedium),
            const SizedBox(height: 16),
            TextFormField(
                controller: _name,
                decoration:
                    const InputDecoration(labelText: 'Уникальное имя *'),
                validator: (value) => (value?.trim().length ?? 0) < 2
                    ? 'Минимум 2 символа'
                    : null),
            const SizedBox(height: 12),
            if (!_isSimulated) ...[
              TextFormField(
                  controller: _address,
                  decoration: const InputDecoration(
                      labelText: 'IP или hostname *', hintText: '192.168.1.1'),
                  validator: (value) =>
                      value?.trim().isEmpty == true ? 'Укажите адрес' : null),
              const SizedBox(height: 12),
            ],
            DropdownButtonFormField(
                key: ValueKey('device-type-$_type'),
                initialValue: _type,
                decoration: const InputDecoration(labelText: 'Тип'),
                items: const [
                  DropdownMenuItem(
                      value: 'router', child: Text('Маршрутизатор')),
                  DropdownMenuItem(value: 'switch', child: Text('Коммутатор')),
                  DropdownMenuItem(value: 'server', child: Text('Сервер')),
                  DropdownMenuItem(value: 'pc', child: Text('Компьютер')),
                  DropdownMenuItem(value: 'printer', child: Text('Принтер')),
                  DropdownMenuItem(
                      value: 'access_point', child: Text('Точка доступа')),
                  DropdownMenuItem(value: 'other', child: Text('Другое')),
                ],
                onChanged: (value) => setState(() => _type = value!)),
            const SizedBox(height: 12),
            if (!_isSimulated) ...[
              DropdownButtonFormField(
                  initialValue: _profile,
                  decoration:
                      const InputDecoration(labelText: 'Профиль мониторинга'),
                  items: const [
                    DropdownMenuItem(value: 'icmp', child: Text('Только ICMP')),
                    DropdownMenuItem(
                        value: 'icmp_snmp', child: Text('ICMP + SNMP')),
                    DropdownMenuItem(
                        value: 'test_agent', child: Text('Тестовый агент')),
                  ],
                  onChanged: (value) => setState(() => _profile = value!)),
              const SizedBox(height: 12),
            ],
            TextFormField(
                controller: _location,
                decoration: const InputDecoration(labelText: 'Расположение')),
            if (_testResult != null)
              Padding(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: Text(_testResult!)),
            const SizedBox(height: 16),
            if (!_isSimulated) ...[
              OutlinedButton.icon(
                  onPressed: _busy ? null : _test,
                  icon: const Icon(Icons.wifi_find),
                  label: const Text('Проверить ICMP')),
              const SizedBox(height: 8),
            ],
            FilledButton(
                onPressed: _busy ? null : _save,
                child: _busy
                    ? const SizedBox.square(
                        dimension: 20,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : const Text('Сохранить')),
          ]),
        ),
      );

  Future<void> _test() async {
    if (_isSimulated) {
      setState(() => _testResult =
          'ДЕМО / СИМУЛЯЦИЯ: ICMP не отправляется. Виртуальное устройство будет доступно после сохранения.');
      return;
    }
    if (_address.text.trim().isEmpty) return;
    setState(() => _busy = true);
    try {
      final result =
          await ref.read(repositoryProvider).testTarget(_address.text.trim());
      setState(() => _testResult =
          '${result['success'] == true ? 'Ответ получен' : 'Нет ответа'}: ${result['detail']}');
    } catch (error) {
      setState(() => _testResult = apiErrorMessage(error));
    } finally {
      setState(() => _busy = false);
    }
  }

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await ref.read(repositoryProvider).addDevice({
        'name': _name.text.trim(),
        'address': _address.text.trim(),
        'device_type': _type,
        'monitoring_profile': _profile,
        'location':
            _location.text.trim().isEmpty ? null : _location.text.trim(),
        'check_interval': 30,
        'is_simulated': _isSimulated,
      });
      ref.invalidate(devicesProvider);
      if (mounted) context.pop();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(apiErrorMessage(error))));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}
