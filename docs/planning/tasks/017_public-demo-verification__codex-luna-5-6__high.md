# T-017 — hosted verification, security and rollback

**Target:** the owner's existing Frankfurt `flowstead-demo-instance` (`VM.Standard.E2.1.Micro`, Oracle Linux 9.8, x86_64). This task checks the **actual deployed instance**, not a different VM. Start assigned work without planning-status checkpoints. Do not invent live-service evidence when components are absent.

## Baseline and acceptance

- Root `AGENTS.md` and the current implementation/spec/deployment runbooks govern actual commands and safety. Keep `@darizae/marisma@0.2.0` and the approved UI layouts.
- **OCI:** verify RUNNING state, SSH limited to owner CIDR, no direct public 8000/4222/8222/5432/6543, current cost and use, available memory, swap and storage, narrow systemd permissions and HTTPS-only ingress. A live system must survive a bounded restart and respect planned OFF; never create another VM or force load to prevent reclamation.
- **Database:** query only existing `flowstead-demo` app/schema (no `flowstead-dev`), confirm `003_jetstream_messages`, 5 fictional Plants and 43,800 M1 rows, data digest and 5 ingress events. Audit least-privilege runtime role, TLS hostname verification and Data API isolation; protect migration-owner credentials.
- **Messaging:** exercise actual NATS stream/consumer durability and dispatch/worker lifecycle, idempotent queued→completed twelve-hour forecast, retry caps, persistent queue after worker restart, stale/deduplicated events, and rejected unauthorized writes. Use bounded requests; no stress tests on provider resources.
- **Public browser:** verify existing Vercel frontend at actual HTTPS URL, list/map/detail/history/forecast, CSV/PNG/PDF rendering and responsive/200% scaling, MapLibre attribution and offline errors. Anonymous requests see exactly the five synthetic Plants; never reveal private IDs or fields.
- **Private browser:** real invited identities with disjoint Plant access, JWT expiry/revocation, session and IndexedDB cache isolation, 401/404 on forged/downgraded/expired credentials, safe file exports, no public signup.
- **Security and operations:** real TLS chain, exact allowed origins, restrictive headers, host firewall/NSG, queue/request bounds, provider alerts/actual spend, restart/restore/rollback without destroying the hosted DB. OCI budget alerts are NOT hard caps.

## Required case IDs

- `OPS-M17-OCI-ARM` (**historical ID**): verify live **x86_64** process/image and actual memory footprint on the existing micro host.
- `SEC-M17-OCI-INGRESS`: real externally observed SSH source restriction, HTTPS/redirects and nonpublic API/broker/DB.
- `OPS-M17-OCI-COST`: observed current provider billing/free eligibility/alerts, without promising zero future spend.
- `OPS-M17-OCI-RECOVERY` and `OPS-M17-RECOVER`: real broker/worker persistence and documented safe backup/restore exercise against disposable copy.
- `E2E-M17-PUBLIC`, `E2E-M17-AUTH`, `UI-M17-LIVE`: real API/browser and private-session enforcement at actual deployed URLs.

Record the exact Git/host build identifiers, evidence time, status, URLs (only nonsecret public URLs), and every unrun test as **UNVERIFIED**. If the service, Auth recipient or hosting secret is absent, continue only local/deployment-prep checks, without claiming success or exposing the resource publicly. No paid resource, destructive reset, attack-volume scan, credential disclosure or root-domain edit.

The owner has already instructed continuing with the existing VM and its available resources. Root `AGENTS.md` applies: test, locally commit, merge local `main`, **do not push** without instruction.
