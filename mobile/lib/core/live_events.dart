import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:web_socket_channel/io.dart';

import 'config_store.dart';

final liveEventsProvider = StreamProvider<Map<String, dynamic>>((ref) async* {
  const storage = FlutterSecureStorage(
      aOptions: AndroidOptions(encryptedSharedPreferences: true));
  final token = await storage.read(key: 'access_token');
  final base = ref.watch(serverConfigProvider).valueOrNull;
  if (token == null || base == null) return;
  final http = Uri.parse(base);
  final uri = http.replace(
    scheme: http.scheme == 'https' ? 'wss' : 'ws',
    path: '${http.path}/api/v1/ws/events'.replaceAll('//', '/'),
  );
  final channel = IOWebSocketChannel.connect(uri,
      headers: {'Authorization': 'Bearer $token'});
  ref.onDispose(channel.sink.close);
  await for (final message in channel.stream) {
    final decoded = jsonDecode(message as String);
    if (decoded is Map) yield Map<String, dynamic>.from(decoded);
  }
});
