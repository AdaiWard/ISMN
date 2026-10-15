import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/repository.dart';
import '../../core/status_ui.dart';

class UsersScreen extends ConsumerWidget {
  const UsersScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final value = ref.watch(usersProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Пользователи')),
      floatingActionButton: FloatingActionButton.extended(
          onPressed: () => _add(context, ref),
          icon: const Icon(Icons.person_add_outlined),
          label: const Text('Создать')),
      body: AsyncPanel(
        value: value,
        retry: () => ref.invalidate(usersProvider),
        data: (items) => ListView.builder(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
          itemCount: items.length,
          itemBuilder: (_, index) {
            final item = items[index];
            return Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  leading:
                      const CircleAvatar(child: Icon(Icons.person_outline)),
                  title: Text(item['username'] as String),
                  subtitle: Text('Роль: ${item['role']}'),
                  trailing: Icon(
                      item['is_active'] == true
                          ? Icons.check_circle
                          : Icons.block,
                      color: item['is_active'] == true
                          ? Colors.green
                          : Colors.red),
                ));
          },
        ),
      ),
    );
  }

  Future<void> _add(BuildContext context, WidgetRef ref) async {
    final username = TextEditingController();
    final password = TextEditingController();
    var role = 'viewer';
    final accepted = await showDialog<bool>(
        context: context,
        builder: (context) => StatefulBuilder(
            builder: (context, setState) => AlertDialog(
                  title: const Text('Новый пользователь'),
                  content: Column(mainAxisSize: MainAxisSize.min, children: [
                    TextField(
                        controller: username,
                        decoration: const InputDecoration(
                            labelText: 'Имя пользователя')),
                    const SizedBox(height: 12),
                    TextField(
                        controller: password,
                        obscureText: true,
                        decoration: const InputDecoration(
                            labelText: 'Пароль (не менее 12 символов)')),
                    const SizedBox(height: 12),
                    DropdownButtonFormField(
                        initialValue: role,
                        decoration: const InputDecoration(labelText: 'Роль'),
                        items: const [
                          DropdownMenuItem(
                              value: 'viewer', child: Text('Наблюдатель')),
                          DropdownMenuItem(
                              value: 'operator', child: Text('Оператор')),
                          DropdownMenuItem(
                              value: 'admin', child: Text('Администратор')),
                        ],
                        onChanged: (value) => setState(() => role = value!)),
                  ]),
                  actions: [
                    TextButton(
                        onPressed: () => Navigator.pop(context, false),
                        child: const Text('Отмена')),
                    FilledButton(
                        onPressed: () => Navigator.pop(context, true),
                        child: const Text('Создать'))
                  ],
                )));
    if (accepted != true || !context.mounted) return;
    try {
      await ref.read(repositoryProvider).addUser({
        'username': username.text.trim(),
        'password': password.text,
        'role': role
      });
      ref.invalidate(usersProvider);
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(apiErrorMessage(error))));
      }
    } finally {
      username.dispose();
      password.dispose();
    }
  }
}
