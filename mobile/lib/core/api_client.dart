import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'config_store.dart';

final apiClientProvider = Provider<Dio>((ref) {
  final baseUrl = ref.watch(serverConfigProvider).valueOrNull ??
      ServerConfigNotifier.fallback;
  const storage = FlutterSecureStorage(
      aOptions: AndroidOptions(encryptedSharedPreferences: true));
  final dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 5),
      receiveTimeout: const Duration(seconds: 10)));
  dio.interceptors.add(InterceptorsWrapper(onRequest: (options, handler) async {
    final token = await storage.read(key: 'access_token');
    if (token != null) options.headers['Authorization'] = 'Bearer $token';
    handler.next(options);
  }, onError: (error, handler) async {
    final isAuthRoute = error.requestOptions.path.contains('/auth/');
    if (error.response?.statusCode == 401 && !isAuthRoute) {
      final refresh = await storage.read(key: 'refresh_token');
      if (refresh != null) {
        try {
          final tokenClient = Dio(BaseOptions(
              baseUrl: baseUrl, connectTimeout: const Duration(seconds: 5)));
          final response = await tokenClient
              .post('/api/v1/auth/refresh', data: {'refresh_token': refresh});
          final data = Map<String, dynamic>.from(response.data as Map);
          await storage.write(
              key: 'access_token', value: data['access_token'] as String);
          await storage.write(
              key: 'refresh_token', value: data['refresh_token'] as String);
          error.requestOptions.headers['Authorization'] =
              'Bearer ${data['access_token']}';
          handler.resolve(await dio.fetch(error.requestOptions));
          return;
        } catch (_) {
          await storage.deleteAll();
        }
      }
    }
    handler.next(error);
  }));
  return dio;
});

String apiErrorMessage(Object error) {
  if (error is DioException) {
    final detail = error.response?.data is Map
        ? (error.response?.data as Map)['detail']
        : null;
    if (detail is String) return detail;
    if (error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout) {
      return 'Сервер недоступен. Проверьте адрес и сеть.';
    }
  }
  return 'Не удалось выполнить запрос';
}
