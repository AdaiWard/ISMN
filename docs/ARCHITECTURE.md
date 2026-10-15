# Архитектура ISMN

## Назначение и границы

Цель — наблюдать только зарегистрированные администратором узлы принадлежащей ему LAN, сохранять факты наблюдения и выполнять лишь ограниченные, аудируемые реакции. Телефон является панелью; мониторинг выполняется сервером.

```mermaid
flowchart LR
    A[Flutter Android] -->|REST + JWT| B[FastAPI]
    B -->|WebSocket + JWT| A
    B --> C[(SQLite на сервере)]
    D[Async scheduler] --> E[ICMP subprocess]
    D --> F[SNMPv3 authPriv]
    E --> G[Allowlisted LAN devices]
    F --> G
    D --> H[Rule + baseline engine]
    H --> I[Incident / safe automation]
    I --> C
    B --> C
```

Backend разделён на API, core/security, SQLAlchemy DB, monitoring, automation, services и Pydantic schemas. Flutter разделён на app, core (API/auth/config/repository/router) и feature screens.

## Поток проверки и инцидента

```mermaid
sequenceDiagram
    participant S as Scheduler
    participant P as ICMP/SNMP
    participant D as SQLite
    participant R as Rule engine
    participant M as Mobile
    S->>P: bounded check with timeout
    P-->>S: exact protocol result
    S->>D: check + metric sample
    S->>R: consecutive state/result
    alt 3 ICMP misses
      R->>D: open one explained incident
      R->>D: create dry-run/safe run + audit
      R-->>M: authenticated WebSocket event
    else 2 successful checks after failure
      R->>D: mark recovered + timeline event
      R-->>M: recovery event
    end
```

## Основные сущности

```mermaid
erDiagram
    USERS ||--o{ REFRESH_TOKENS : owns
    USERS ||--o{ AUDIT_LOGS : acts
    DEVICE_GROUPS ||--o{ DEVICES : groups
    DEVICE_CREDENTIALS ||--o{ DEVICES : assigned
    DEVICES ||--o{ MONITORING_CHECKS : observed
    DEVICES ||--o{ METRIC_SAMPLES : measures
    DEVICES ||--o{ DEVICE_INTERFACES : exposes
    DEVICES ||--o{ INCIDENTS : raises
    INCIDENTS ||--o{ INCIDENT_EVENTS : timeline
    AUTOMATION_RULES ||--o{ AUTOMATION_RUNS : executes
    INCIDENTS ||--o{ AUTOMATION_RUNS : triggers
    DEVICES ||--o{ NETWORK_LINKS : manual
```

Также существуют `alert_rules`, `notifications`, `app_settings`. Внешние ключи SQLite включены через `PRAGMA foreign_keys=ON`; критичные поля индексированы.

## Протоколы

- REST/JSON и OpenAPI — управление и polling fallback.
- WebSocket — live events с access token.
- ICMP — только достижимость, фиксированное число пакетов и timeout.
- SNMPv3 authPriv — стандартные поддерживаемые OID; SNMPv2c в core не включён.
- SSH — архитектурно предусмотрен, но произвольные/непроверенные команды не реализованы. UI/API честно блокирует такую попытку.

## Объяснимая «интеллектуальность»

Core использует детерминированные правила, гистерезис и функцию moving median baseline. Каждое событие хранит наблюдение и объяснение. При менее чем 10 образцах baseline возвращает «Недостаточно данных». Это не ML и проект этого не заявляет.

## Функциональные требования

Регистрация устройств, фоновые проверки, история, состояния, инциденты, live events, RBAC, отчёты, ручная топология, аудит и безопасная автоматизация. Нефункциональные: local-first, восстановление после рестарта, bounded concurrency, отсутствие plaintext-секретов в API, русская доступная UI, явное разделение real/simulated.

