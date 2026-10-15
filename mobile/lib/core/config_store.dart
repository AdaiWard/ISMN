import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ServerConfigNotifier extends AsyncNotifier<String> {
  static const fallback = 'http://10.0.2.2:8000';

  @override
  Future<String> build() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('server_url') ?? fallback;
  }

  Future<void> save(String raw) async {
    var value = raw.trim();
    if (!value.startsWith('http://') && !value.startsWith('https://')) {
      value = 'http://$value';
    }
    value = value.replaceFirst(RegExp(r'/$'), '');
    final uri = Uri.tryParse(value);
    if (uri == null ||
        uri.host.isEmpty ||
        !{'http', 'https'}.contains(uri.scheme)) {
      throw const FormatException('Введите корректный адрес сервера');
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('server_url', value);
    state = AsyncData(value);
  }
}

final serverConfigProvider =
    AsyncNotifierProvider<ServerConfigNotifier, String>(
        ServerConfigNotifier.new);
