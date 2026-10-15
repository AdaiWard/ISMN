# Демонстрация и защита диплома

## Актуальность, цель, задачи

Актуальность — малым организациям и учебным лабораториям нужен наблюдаемый local-first контроль без обязательного облака. Цель — реализовать проверяемый мониторинг LAN с мобильной панелью и безопасной автоматической реакцией. Задачи: модель данных, RBAC, реальный ICMP/SNMP, планировщик, гистерезис, события, объяснимые правила, отчёты, Flutter UI и документированная защита от опасных действий.

## Роли и use cases

- Администратор: пользователи, devices/credentials, правила, pause, topology, аудит.
- Оператор: наблюдение, ручная проверка, acknowledge.
- Наблюдатель: read-only dashboard/history/reports.

## Сценарий показа

1. Запустить миграции/backend, войти через Android и показать, что после рестарта история остаётся.
2. Добавить свой lab device, выполнить ICMP и проговорить ограничение протокола.
3. Изолировать test device. После трёх неуспехов показать Offline, один critical incident, timeline, SQLite history и live WebSocket update.
4. Вернуть связь. После двух успехов показать recovery и закрытие инцидента.
5. Показать dry-run rule, audit record и emergency pause. Подчеркнуть: неподготовленная SSH-команда блокируется.
6. Добавить «Демо-устройство», открыть его карточку и отключить разрешённый виртуальный порт после подтверждения. Показать метку `ДЕМО / СИМУЛЯЦИЯ`, изменившееся состояние и запись `demo.control` в аудите.
7. Попытаться изменить виртуальный UPLINK: сервер должен отклонить действие.
6. Показать отчёт доступности за наблюдавшийся период и CSV endpoint.
7. При отсутствии SNMP hardware выполнить `python -m scripts.seed_demo` и открыть помеченные `ДЕМО / СИМУЛЯЦИЯ` записи. Никогда не называть их физическими измерениями.

## Тест-кейсы для комиссии

| Случай | Ожидание |
|---|---|
| Viewer создаёт device | 403 |
| IP вне allowlist | 422 |
| Повторный IP | 409 |
| 1–2 ICMP misses | не Offline |
| 3-й miss | Offline + один incident |
| 2 success после отказа | Online + resolved timeline |
| SNMP timeout | объяснённая ошибка, без fake metrics |
| dry-run automation | `simulated`, действие не исполнено |
| uplink/trunk action | blocked |
| WebSocket без token | закрытие 4401 |

## Скриншоты для пояснительной записки

Login/server setup; dashboard; device wizard; device history/chart; incident timeline; automation DRY-RUN и pause; manual topology banner; availability report; OpenAPI; SQLite persistence после рестарта; pytest result; real-vs-simulated banner.

## Ограничения

Нет автоматического LLDP/CDP discovery, Syslog ingestion, обученного ML, проверенного vendor SSH driver и физической SNMP/SSH валидации в текущем окружении. Flutter SDK также отсутствовал, поэтому APK и widget tests требуют запуска на машине с Flutter. Эти ограничения не скрываются и не заменяются фиктивными success-сообщениями.

