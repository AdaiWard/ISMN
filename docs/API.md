# API ISMN

База: `/api/v1`; интерактивная схема: `/docs`; OpenAPI JSON: `/openapi.json`.

## Сессии

- `POST /auth/login`, `/auth/refresh`, `/auth/logout`; `GET /auth/me`.
- Access token передаётся как `Authorization: Bearer …`.
- Refresh token хранится сервером только в SHA-256 digest, вращается при refresh и отзывается при logout.

## Ресурсы

- `/users` — admin-only создание/список.
- `/credentials/snmpv3` — admin-only, secret values никогда не возвращаются.
- `/devices` — список, создание, изменение, архив; `/test-target`, `/{id}/test`, `/{id}/check`.
- `/devices/{id}/checks`, `/devices/{id}/metrics` — история и графики.
- `/dashboard` — серверные агрегаты.
- `/incidents`, `/{id}/events`, `/{id}/acknowledge` — центр инцидентов.
- `/automations/status`, `/pause`, `/rules`, `/runs` — safe lifecycle.
- `GET /devices/{id}/interfaces` — интерфейсы устройства.
- `POST /devices/{id}/demo-actions` — только подтверждённые симулированные действия над устройством с `is_simulated=true`; реальные устройства и защищённые интерфейсы отклоняются.
- `/reports/availability` и `.csv` — наблюдаемая доступность.
- `/topology` — только ручные связи.
- `/audit` — immutable через публичный API, admin-only чтение.
- `WS /ws/events` — аутентифицированный live stream; access token передаётся в заголовке `Authorization`, а не в URL.

Списки используют `limit`/`offset`. Ошибки возвращают `{"detail":"…"}`. `409` обозначает конфликт/текущее состояние, `422` — validation/allowlist, `401/403` — authentication/authorization.

