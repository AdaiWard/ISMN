# ISMN — Intelligent System for Monitoring and Network Management

Система мониторинга и управления локальной сетью: ICMP/SNMPv3, отслеживание инцидентов, автоматизация с подтверждением действий и мобильная панель на Flutter. Сервер на FastAPI хранит данные локально в SQLite.

## Структура проекта

- `backend/` — API, мониторинг, автоматизация, миграции и тесты.
- `mobile/` — приложение Flutter для Android.
- `docs/` — архитектура, настройка сети, API и материалы дипломного проекта.

Важно: ICMP подтверждает достижимость, но не исправность CPU/RAM, питания или кабеля. Отсутствие ответа может означать фильтрацию ICMP. Неподдерживаемые метрики не генерируются.

## Что реализовано

- JWT access token + вращаемые и отзываемые refresh-сессии, Argon2id, роли admin/operator/viewer и ограничение попыток входа.
- CRUD устройств с проверкой IP/hostname по CIDR allowlist и архивированием вместо физического удаления.
- Планировщик на сервере, безопасный системный `ping` без shell, ограничение параллелизма, 3 отказа до Offline и 2 успеха до восстановления.
- SQLite-история проверок/метрик/событий, инциденты без alert storm, аудит, WebSocket и REST fallback.
- SNMPv3 authPriv для стандартных `sysName`/`sysUpTime`; шифрование профилей. Vendor CPU/RAM намеренно не угадываются.
- Dry-run/manual-approval автоматизация, emergency pause и блокировка uplink/trunk/management-интерфейсов.
- Dashboard, устройства, мастер добавления/тест, график задержки, инциденты, топология, автоматизация, отчёты, пользователи и настройки в Flutter.
- Детерминированный demo seed, всегда помеченный `ДЕМО / СИМУЛЯЦИЯ` и `is_simulated=true`.
- Безопасное демо-управление виртуальным устройством: диагностика, перезагрузка, включение/отключение и перезапуск разрешённых интерфейсов. Каждое действие требует подтверждения, записывается в аудит и никогда не отправляет команду в реальную сеть; uplink/trunk/WAN защищены.

## Демо-управление

В мобильном мастере добавления включите «Демо-устройство», выберите тип (например, «Коммутатор») и сохраните запись. Адрес создаётся сервером в домене `simulation.local`, реальные ICMP/SNMP/SSH-команды не выполняются. В карточке устройства появится блок «Демо-управление» с виртуальными интерфейсами и обязательным подтверждением операций.

## Быстрый запуск backend на Windows

Требуется Python 3.12+. Склонируйте репозиторий и откройте каталог проекта в PowerShell:

```powershell
git clone https://github.com/AdaiWard/ISMN.git
cd ISMN
```

Подготовьте backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env  # если .env ещё нет
# Замените ISMN_SECRET_KEY на результат: python -c "import secrets; print(secrets.token_urlsafe(48))"
python -m alembic upgrade head
python -m scripts.create_admin --username admin
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

OpenAPI: `http://127.0.0.1:8000/docs`. Проверка: `http://127.0.0.1:8000/health/ready`.

Для телефона запуск на `0.0.0.0` разрешайте только в доверенной учебной LAN после ограничения Windows Firewall; детали в [NETWORK_SETUP.md](docs/NETWORK_SETUP.md).

## Flutter Android

Требуются Flutter SDK, Android SDK и JDK 17. Android-проект уже включён в репозиторий. Из корня проекта:

```powershell
cd mobile
flutter doctor
flutter pub get
flutter analyze
flutter test
flutter run
flutter build apk
```

APK появится в `mobile/build/app/outputs/flutter-apk/app-release.apk`. Android native-конфигурация включает cleartext HTTP только для debug; release требует HTTPS. На эмуляторе используйте `http://10.0.2.2:8000`, на телефоне — LAN IP компьютера.

Текущая release-конфигурация использует debug-подпись для учебной сборки. Для публикации приложения настройте собственный ключ подписи вне репозитория.

Локальные `.env`, базы SQLite, ключи подписи, кэши и результаты сборки исключены из Git. Для новой установки создайте собственный `.env` из `backend/.env.example` и задайте уникальный `ISMN_SECRET_KEY`.

## Проверки

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Автотесты покрывают login/refresh/logout, RBAC, device CRUD и дубликаты, CIDR allowlist, ICMP parsing/timeout, durable metrics, hysteresis/recovery, подавление повторных инцидентов, SNMP timeout/counter wrap, dry-run/pause, forbidden interfaces, WebSocket auth и агрегацию отчёта.

## Документация

- [Архитектура](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [Настройка сети](docs/NETWORK_SETUP.md)
- [Безопасность](docs/SECURITY.md)
- [Сценарий защиты диплома](docs/DEMO_DEFENSE.md)

