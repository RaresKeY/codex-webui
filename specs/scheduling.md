# Scheduling

Scheduling is server-owned in `backend/app/scheduler.py` using APScheduler. A SQLite record stores name, prompt, `interval` or five-field cron expression, validated workspace-relative path, optional thread ID, enabled flag, and last run/status/error summary. The scheduler is UTC-only. Interval values are seconds with a 10-second minimum; cron uses `CronTrigger.from_crontab`.

Jobs use `coalesce=True`, `max_instances=1`, and replace-by-task ID. An in-process task-ID lease prevents overlap between scheduled and manual runs. A run resumes with the configured working directory or starts a thread there using exact `on-request` approval and `workspace-write` sandbox modes, starts a turn, waits for the matching `turn/completed`, and persists terminal status/error. Stop cancels active scheduler tasks.

## Gaps

- UI create, enable/disable, and run-now are live; edit/delete and visible error/history detail remain incomplete.
- The lease and completion wait are in-process only: there is no persisted execution row/idempotency lease, restart reconciliation, retry policy, timeout, or pending-approval notification.
- Decide timezone/DST and unattended approval behavior; add restart and multi-instance duplicate tests.
