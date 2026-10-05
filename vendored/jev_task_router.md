# Jev task-router interface

`backend/app/routing_policy.json` is the owning user's V5 policy snapshot from `../jev-task-router` on 2026-10-05. `task_router.py` adapts its two compact typed questions and strict maximizing-Choice validation to interactive text chat. No Python package or JavaScript dependency is added for Jev.

Endpoint/model are inherited from the router's standard-library transport: `https://api.typesafe.ai/v1/systemone`, `jev-1.13.0`. Allowed execution models remain `gpt-6.1-sol` and `gpt-6-luna`; effort remains low/medium/high/xhigh/max. Credentials are environment or external-file data, never embedded. Interactive requests do not mutate router study ledgers, frozen asks or reports. The web adapter records no raw evidence or historical inputs.

## Gaps

- The snapshot is not synchronized automatically; policy updates require comparing the owning router's spec and tests.
- Provider confidence and downstream task success remain uncalibrated; no paid integration smoke here.
