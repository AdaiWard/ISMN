# Подключение в локальной сети

## Windows PC + Android

1. Узнайте IPv4 компьютера командой `ipconfig` и убедитесь, что телефон подключён к той же доверенной Wi‑Fi/LAN.
2. В `.env` сузьте `ISMN_ALLOWED_NETWORKS` до фактической лабораторной подсети, например `["192.168.10.0/24"]`.
3. Сначала проверьте backend на `127.0.0.1`. Для телефона запустите явно: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`.
4. Создайте inbound firewall rule только для TCP/8000, только для Private profile и только для нужной подсети. Не открывайте порт на Public profile/Internet.
5. В приложении укажите `http://<LAN-IP-PC>:8000`. `localhost` на телефоне означает сам телефон; Android emulator использует `10.0.2.2`.

Debug Android manifest явно разрешает cleartext для лаборатории. Release этого не делает. Для реального использования поставьте Caddy/Nginx перед Uvicorn, выпустите доверенный локальный сертификат, используйте `https://`/`wss://` и ограничьте CORS/firewall.

## Узлы

- Windows/Linux PC: разрешите ICMP echo только из monitoring host, если это соответствует политике.
- Домашний router: сначала используйте ICMP; SNMP включайте лишь если устройство поддерживает SNMPv3 authPriv.
- GNS3/EVE-NG: подключите management-интерфейс appliance к достижимой host-only/bridged сети.
- Packet Tracer сам по себе не гарантирует доступ внешнего Python к виртуальным устройствам; не демонстрируйте его как реальный end-to-end без проверенного bridge.

Не сканируйте Internet или чужие подсети. ISMN не выполняет broad discovery: каждый адрес добавляется вручную и сверяется с allowlist.

