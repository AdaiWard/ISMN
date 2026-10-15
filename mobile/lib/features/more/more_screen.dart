import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Инструменты')),
        body: ListView(padding: const EdgeInsets.all(16), children: [
          _tile(context, Icons.account_tree_outlined, 'Топология',
              'Ручные, честно обозначенные связи', '/topology'),
          _tile(context, Icons.auto_fix_high_outlined, 'Автоматизация',
              'Dry-run, одобрения и аварийная пауза', '/automation'),
          _tile(context, Icons.assessment_outlined, 'Отчёты',
              'Наблюдаемая доступность и задержка', '/reports'),
          _tile(context, Icons.manage_accounts_outlined, 'Пользователи',
              'Администраторы, операторы и наблюдатели', '/users'),
          _tile(context, Icons.settings_outlined, 'Настройки',
              'Адрес API, профиль и выход', '/settings'),
        ]),
      );

  Widget _tile(BuildContext context, IconData icon, String title,
          String subtitle, String path) =>
      Card(
        margin: const EdgeInsets.only(bottom: 8),
        child: ListTile(
            leading: Icon(icon),
            title: Text(title),
            subtitle: Text(subtitle),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push(path)),
      );
}
