# ISMN engineering conventions

- Keep the backend local-first: FastAPI owns monitoring, automation and the SQLite database.
- Never fabricate real telemetry. Simulator records must keep `is_simulated=true` and be shown as DEMO/SIMULATION.
- Network targets must pass the configured CIDR allowlist. Never add broad discovery or user-provided shell execution.
- All secrets stay outside source control. API responses never expose credential material.
- Automation defaults to dry-run; active actions require an explicit rule, device permission and approval.
- Use SQLAlchemy sessions through `app.db.session.get_db`; preserve audit history.
- Add or update pytest coverage for backend behavior. Run `pytest` from `backend`.
- Flutter uses Riverpod, GoRouter and the centralized API client. UI text is Russian-first and localization-ready.

