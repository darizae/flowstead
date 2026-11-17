# Flowstead implementation agent routing

**Primary route:** read `docs/planning/HANDOFF_SEQUENCE.md` to identify the **one approved, READY executable task**; then read that task file and `docs/planning/IMPLEMENTATION_SPEC.md` plus its initial read set. Do not treat a high-level milestone marked PLANNED/PREPARED as queue authorization.

This repository owns Flowstead application API, versioned PostgreSQL schema/migrations, bounded synthetic importer, Supabase Auth adapter, React UI, forecasts and permission-scoped exports. The independent upstream is `darizae/flowstead-sim`; pin an immutable tested generator version/commit, never vendor its code. **PostgreSQL-only for MVP; no AWS S3**, object-store setup or persistent report file store. D-040 is owner-approved; cloud writes, new `flowstead-demo`, Auth invitations, hosting and DNS still require separate exact approval.

Use root `justfile` local commands only when real recipes exist. Preserve uncommitted owner work, secret boundaries and tight changed-path/lockfile preflight; test first on the Mac. Worktree isolation is not OS sandboxing. No DHI-derived published data, forced Git history rewrites, arbitrary model-supplied shell, unbounded export or unrelated refactor.

**OMP implements/tests; only ChatGPT normal chat in the pinned Loop OMP Project independently reviews PRs and makes direct GitHub corrections.** Exact-head Mac re-verification and authorized merge/cleanup are mandatory. The control-plane repository holds task receipts and dashboard status, not the Flowstead source-of-truth plan.
