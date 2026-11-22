# T-020 — hosted operator login and live validation

**Repository:** darizae/flowstead. **Priority:** closes the remaining hosted
acceptance of T-017 with the already-deployed live stack; no new cloud resource.

## Status baseline (verified, 2026-11-22)

Reconcile against the [live verification receipt](../../deployment/T017_LIVE_VERIFICATION_2026-11-21.md)
and the checked-in deploy commits on local `main`:

- **Backend deployed** 2026-11-22: `flowstead-api`, `flowstead-worker`,
  `flowstead-nats` and `flowstead-proxy` systemd units active on the existing
  Frankfurt E2.1.Micro; live HTTPS health/ready return 200 JSON, public five-Plant
  reads and the Plant PDF report return 200, unknown Plant returns 404.
- **Auth users created**: two non-deliverable test operators (`*-a@example.invalid`,
  `*-b@example.invalid`) confirmed in `auth.users` with disjoint scoped grants
  (A: plant-01, plant-02; B: plant-03, plant-04, plant-05). No test passwords or
  tokens are in Git.
- **Events published**: the five original `app.message_outbox` rows moved
  pending → published; `app.message_failures` is 0, NATS shows one stream/one
  consumer/five stored messages. This proves publishing, not a processed forecast.
- **Forecast jobs**: `app.forecast_jobs` and `app.forecast_issuances` still have
  **zero** rows (2026-11-22). A queued → completed forecast has not yet run live.
- **Costs**: actual OCI/Supabase/Vercel charges and hard-cap controls remain
  **outstanding**; no paid resource has been provisioned by this work.

**Execution status: PARTIAL.** Implementation and measured results are recorded
in [T-020 progress](../../deployment/T020_PROGRESS_2026-11-22.md).
A real Supabase password grant succeeded for each test account using protected,
owner-local files without exposing the passwords/JWTs. The React login UI is
implemented and locally tested. Production API/GUI browser E2E is blocked by
an Oracle guest timeout/restart and is **not** a PASS. The remaining T-017
scope below is still required.

## Scope

1. **Authenticated live browser sessions** for both confirmed test operators on
   the deployed frontend, and one negative anonymous/revoked session.
2. **Real JWT cross-Plant authorization** against the live API: operator A cannot
   read operator B's Plants (and vice versa); expired/forged/revoked tokens are
   denied 401; errors do not enumerate Plant/identity existence.
3. **Forecast request → worker → stored forecast**: submit an authorized forecast
   through the API, observe the queued row move to completed, and read a stored
   deterministic 12-hour forecast; confirm outbox/NATS backpressure and job bounds.
4. **Export/report access isolation**: per-operator CSV/PNG/PDF availability maps
   exactly to the projected Plant grant; unauthorized Plants fail closed.
5. **Broker/proxy restart recovery**: restart `flowstead-nats` and
   `flowstead-proxy` (bounded, at a quiet moment) and confirm JetStream persistence
   and the HTTPS API recover without data loss.
6. **Cost reconciliation**: observe current OCI/Supabase/Vercel usage, budget
   alerts and free-tier eligibility; record PASS/UNVERIFIED, never claim hard caps
   from alert-only safeguards.

## Guardrails

- Use only the deployed `flowstead-demo-instance` and both already-created test
  operators. Do not create a VM, invite additional users, rotate credentials,
  launch paid resources or run load/attack traffic. Never commit tokens, private
  connection strings, test passwords, OCIDs, emails or billing identifiers.
- No changes to `frontend/src/` or `backend/src/` are assumed; any required
  runtime fix must be separately justified and scoped before editing source.
- Record each check with the actual Git/build identifiers and evidence time,
  marking anything not independently observed as UNVERIFIED/BLOCKED.

## Completion rule

This task closes only when a completed live forecast, both signed-in operator
sessions with the disjoint-access matrix, restart recovery and an observed cost
status are recorded. A mocked or plan-only result cannot close it; do not report
E2E pass without the live evidence.