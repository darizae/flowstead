# Flowstead — forecast_job status requester-scoping fix and cost/abuse residual note (redacted)

- **Date:** 2026-11-22
- **Fix scope:** `backend/src/flowstead_api/message_store.py` `read_forecast_job` + focused integration test in `backend/tests/integration/test_messaging.py`.
- **Status:** fix **LOCAL VERIFIED by code/test design**; DB-backed runtime verification **BLOCKED in this sandbox** (no Docker/PostgreSQL). No credential, key, OCID, public IP or environment value is printed herein.

## 1. Vulnerability fixed (cross-requester forecast status)

`read_forecast_job` filtered `forecast_jobs` only by `correlation_id` and Plant-membership
(via `operator_plant_access`). A signed-in operator who belongs to the same Plant as another
requester could observe that requester's forecast job status by guessing/learning a
`correlation_id`. This leaked job lifecycle state (queued/completed/failed/diagnostic)
across requesters within a Plant.

**Fix:** the status SELECT now also requires `j.requested_by = subject_id`, in addition to the
Plant grant:

```sql
WHERE j.correlation_id = %s
  AND j.requested_by = %s
  AND access.subject_id = %s
```

The `requested_by` binding is the definitive requester check; the Plant-grant join is kept so a
requester whose Plant access was revoked can no longer poll a job. Reads of a non-owned job
resolve to `None` and the route returns the existing uniform, non-enumerating `404` (same body
as an unknown `correlation_id`), so no requester identity is disclosed.

**Regression test** (`test_forecast_status_is_requester_scoped_across_shared_plant_reads`,
case SEC-M19-AUTHZ):
- seeds a shared-Plant requester (`operator-shared`) granted only `plant-01`;
- `operator-a` enqueues a forecast for `plant-01`;
- `operator-shared` reading that job returns `404` identical to an unknown `correlation_id`,
  and the body contains no requester identity;
- the owning requester still reads their own job (`200`), and the shared user reads their own
  enqueued job (`200`).

## 2. Forecast rate-limit / idempotency / retention assessment

| Dimension | Current state (verified in code) | Verdict |
|---|---|---|
| Submission rate limit | Per-principal **and** per-Plant limiter before enqueue (`security.py`, env-tunable `FLOWSTEAD_FORECAST_RATE_LIMIT_REQUESTS`/`_WINDOW_SECONDS`, default 30/60); 429 + `Retry-After`. | **Covered.** Bounded per identity. |
| Delivery idempotency | Worker persists inbox receipt keyed by `event_id` and a deterministic issuance; JetStream duplicate redelivery cannot double-create a forecast (`test_real_jetstream_flow_duplicate_outage_poison_and_retry_exhaustion`). | **Covered.** |
| Storage retention | `forecast_jobs` and drained `message_outbox` terminal rows are **never pruned**; at the default allowed rate (30/60 per principal+Plant) they grow without a clear bound. JetStream stream itself is bounded (7 d / 100 k msgs / 256 MB / 5 deliveries). | **GAP — open.** |

**Why no code change here:** a safe fix for the retention gap is a DB-backed periodic prune of
terminal `forecast_jobs`/outbox rows (older than a retention window), which requires a scheduled
service/worker loop plus a covered test. No such scheduler exists in this repo and this sandbox
cannot run the disposable PostgreSQL to prove and cover it. Making an unproven, uncovered storage
change violates the "small bounded safe changes ONLY if proven and covered" instruction, so the
gap is recorded instead of patched blind.

## 3. Prioritized follow-up (redacted decision queue)

| Priority | Item | Proposed change | Ownership / trigger |
|---|---|---|---|
| P1 | `forecast_jobs`/`message_outbox` terminal-row retention | Add a periodic prune (e.g. in the durable worker) deleting job/outbox rows older than N days, plus a bounded integration test and an explicit retention env default. | Owner, before public launch. Blocked locally: no scheduler, no disposable DB in sandbox. |
| P2 | Optional per-identity+Plant outstanding-job cap | Enforce a maximum number of non-terminal jobs per `requested_by`/Plant in `enqueue_forecast` to bound concurrent backlog. | Only if backlog becomes a real cost signal; not required given 30/60 limit. |
| P3 | Alert on 429 spikes / backlog | Log-backed alert on repeated 429s and `forecast_jobs` backlog growth. | Observability follow-up at deploy. |

No further code change was made beyond the requester-scoping fix; rate-limiting and delivery
idempotency already satisfy their respective bounds.