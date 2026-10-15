# Безопасность и модель угроз

## Допущения

Сервер и устройства находятся в доверенной административной LAN. Угроза включает чужой клиент в LAN, кражу access token, подбор пароля, ошибочную регистрацию внешнего адреса, раскрытие SNMP secrets и опасную автоматизацию. Компрометация ОС сервера/администратора находится за границей приложения и требует системного hardening.

## Контрмеры

- Argon2id password hash, короткий access token, rotating/revocable refresh session, одинаковая ошибка login и in-memory rate limit.
- Серверная RBAC на каждом mutation endpoint; UI hiding не считается контролем доступа.
- CIDR allowlist и DNS resolution validation; нет unrestricted scanner.
- Fernet encryption at rest для SNMP credential payload; master key берётся из environment и secret values не возвращаются.
- Safe ping argument list, timeout и отсутствие `shell=True`; ORM parameterization.
- CORS allowlist, authenticated WebSocket, pagination, bounded check concurrency и per-device lock.
- Dry-run default, global emergency pause, explicit device permission, approval requirement и forbidden interface guard.
- Append-only через API audit trail; sensitive log redaction; SQLite foreign keys/WAL.
- Release Android не разрешает cleartext. HTTPS termination и firewall обязательны вне изолированной лаборатории.

## Операции

Сгенерируйте отдельные `ISMN_SECRET_KEY` и `ISMN_CREDENTIAL_MASTER_KEY`, храните `.env` с ACL только для service account и не меняйте master key без миграции credentials. Регулярно запускайте `python -m scripts.backup <путь>` и проверяйте restore на отдельной копии. Ограничьте retention через `ISMN_METRIC_RETENTION_DAYS`.

Известное ограничение: login rate limiter хранится в памяти одного процесса. Для нескольких workers нужен общий локальный Redis/DB limiter. Проект рекомендуется запускать одним worker, поскольку scheduler также process-local.

