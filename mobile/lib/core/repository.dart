import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

typedef Json = Map<String, dynamic>;

class IsmnRepository {
  IsmnRepository(this.ref);
  final Ref ref;

  Future<Json> dashboard() async => Map<String, dynamic>.from(
      (await ref.read(apiClientProvider).get('/api/v1/dashboard')).data as Map);

  Future<List<Json>> devices({String? search}) async {
    final response = await ref.read(apiClientProvider).get('/api/v1/devices',
        queryParameters: {if (search?.isNotEmpty == true) 'search': search});
    return ((response.data as Map)['items'] as List)
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList();
  }

  Future<Json> device(int id) async => Map<String, dynamic>.from(
      (await ref.read(apiClientProvider).get('/api/v1/devices/$id')).data
          as Map);

  Future<void> addDevice(Json data) =>
      ref.read(apiClientProvider).post('/api/v1/devices', data: data);

  Future<Json> testTarget(String address) async =>
      Map<String, dynamic>.from((await ref
              .read(apiClientProvider)
              .post('/api/v1/devices/test-target', data: {'address': address}))
          .data as Map);

  Future<void> archiveDevice(int id) =>
      ref.read(apiClientProvider).delete('/api/v1/devices/$id');

  Future<Json> checkDevice(int id) async => Map<String, dynamic>.from(
      (await ref.read(apiClientProvider).post('/api/v1/devices/$id/check')).data
          as Map);

  Future<List<Json>> deviceInterfaces(int id) async {
    final response =
        await ref.read(apiClientProvider).get('/api/v1/devices/$id/interfaces');
    return (response.data as List)
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList();
  }

  Future<Json> runDemoAction(int id, String action, {int? interfaceId}) async =>
      Map<String, dynamic>.from(
        (await ref.read(apiClientProvider).post(
          '/api/v1/devices/$id/demo-actions',
          data: {
            'action': action,
            'interface_id': interfaceId,
            'confirmed': true
          },
        ))
            .data as Map,
      );

  Future<List<Json>> metrics(int id) async {
    final response = await ref.read(apiClientProvider).get(
        '/api/v1/devices/$id/metrics',
        queryParameters: {'name': 'ping_latency', 'hours': 24});
    return (response.data as List)
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList();
  }

  Future<List<Json>> incidents() async {
    final response = await ref.read(apiClientProvider).get('/api/v1/incidents');
    return ((response.data as Map)['items'] as List)
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList();
  }

  Future<void> acknowledge(int id) =>
      ref.read(apiClientProvider).post('/api/v1/incidents/$id/acknowledge',
          data: {'note': 'Принято оператором мобильного приложения'});

  Future<Json> automationStatus() async => Map<String, dynamic>.from(
      (await ref.read(apiClientProvider).get('/api/v1/automations/status')).data
          as Map);

  Future<List<Json>> automationRules() async =>
      ((await ref.read(apiClientProvider).get('/api/v1/automations/rules')).data
              as List)
          .map((item) => Map<String, dynamic>.from(item as Map))
          .toList();

  Future<void> setAutomationPaused(bool paused) => ref
      .read(apiClientProvider)
      .put('/api/v1/automations/pause', data: {'paused': paused});

  Future<Json> report() async => Map<String, dynamic>.from(
      (await ref.read(apiClientProvider).get('/api/v1/reports/availability'))
          .data as Map);

  Future<List<int>> availabilityCsv() async {
    final response = await ref.read(apiClientProvider).get<List<int>>(
        '/api/v1/reports/availability.csv',
        options: Options(responseType: ResponseType.bytes));
    return response.data!;
  }

  Future<Json> topology() async => Map<String, dynamic>.from(
      (await ref.read(apiClientProvider).get('/api/v1/topology')).data as Map);

  Future<List<Json>> users() async {
    final response = await ref.read(apiClientProvider).get('/api/v1/users');
    return ((response.data as Map)['items'] as List)
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList();
  }

  Future<void> addUser(Json data) =>
      ref.read(apiClientProvider).post('/api/v1/users', data: data);
}

final repositoryProvider = Provider(IsmnRepository.new);
final dashboardProvider =
    FutureProvider((ref) => ref.read(repositoryProvider).dashboard());
final devicesProvider =
    FutureProvider((ref) => ref.read(repositoryProvider).devices());
final incidentsProvider =
    FutureProvider((ref) => ref.read(repositoryProvider).incidents());
final automationProvider = FutureProvider((ref) async => (
      status: await ref.read(repositoryProvider).automationStatus(),
      rules: await ref.read(repositoryProvider).automationRules(),
    ));
final reportProvider =
    FutureProvider((ref) => ref.read(repositoryProvider).report());
final topologyProvider =
    FutureProvider((ref) => ref.read(repositoryProvider).topology());
final usersProvider =
    FutureProvider((ref) => ref.read(repositoryProvider).users());
final deviceProvider = FutureProvider.family(
    (ref, int id) => ref.read(repositoryProvider).device(id));
final metricsProvider = FutureProvider.family(
    (ref, int id) => ref.read(repositoryProvider).metrics(id));
final deviceInterfacesProvider = FutureProvider.family(
    (ref, int id) => ref.read(repositoryProvider).deviceInterfaces(id));
