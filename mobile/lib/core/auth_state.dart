import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'api_client.dart';

class AuthState {
  const AuthState(
      {this.authenticated = false, this.loading = false, this.error});
  final bool authenticated;
  final bool loading;
  final String? error;

  AuthState copyWith(
          {bool? authenticated,
          bool? loading,
          String? error,
          bool clearError = false}) =>
      AuthState(
        authenticated: authenticated ?? this.authenticated,
        loading: loading ?? this.loading,
        error: clearError ? null : error ?? this.error,
      );
}

class AuthNotifier extends Notifier<AuthState> {
  static const _storage = FlutterSecureStorage(
      aOptions: AndroidOptions(encryptedSharedPreferences: true));

  @override
  AuthState build() {
    _restore();
    return const AuthState(loading: true);
  }

  Future<void> _restore() async {
    final token = await _storage.read(key: 'access_token');
    if (token == null) {
      state = const AuthState();
      return;
    }
    try {
      await ref.read(apiClientProvider).get('/api/v1/auth/me');
      state = const AuthState(authenticated: true);
    } catch (_) {
      final refreshed = await _refresh();
      state = AuthState(authenticated: refreshed);
    }
  }

  Future<bool> signIn(String username, String password) async {
    state = const AuthState(loading: true);
    try {
      final response = await ref.read(apiClientProvider).post(
          '/api/v1/auth/login',
          data: {'username': username, 'password': password});
      await _saveTokens(response.data as Map<String, dynamic>);
      state = const AuthState(authenticated: true);
      return true;
    } catch (error) {
      state = AuthState(error: apiErrorMessage(error));
      return false;
    }
  }

  Future<bool> _refresh() async {
    final refresh = await _storage.read(key: 'refresh_token');
    if (refresh == null) return false;
    try {
      final response = await ref
          .read(apiClientProvider)
          .post('/api/v1/auth/refresh', data: {'refresh_token': refresh});
      await _saveTokens(response.data as Map<String, dynamic>);
      return true;
    } catch (_) {
      await _storage.deleteAll();
      return false;
    }
  }

  Future<void> _saveTokens(Map<String, dynamic> value) async {
    await _storage.write(
        key: 'access_token', value: value['access_token'] as String);
    await _storage.write(
        key: 'refresh_token', value: value['refresh_token'] as String);
  }

  Future<void> signOut() async {
    final refresh = await _storage.read(key: 'refresh_token');
    if (refresh != null) {
      try {
        await ref
            .read(apiClientProvider)
            .post('/api/v1/auth/logout', data: {'refresh_token': refresh});
      } catch (_) {}
    }
    await _storage.deleteAll();
    state = const AuthState();
  }
}

final authProvider =
    NotifierProvider<AuthNotifier, AuthState>(AuthNotifier.new);
