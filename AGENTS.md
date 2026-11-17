# Repository agent instructions

This repository is the private Flowstead application scaffold only. The shared approved contract is `docs/planning/IMPLEMENTATION_SPEC.md`; task order is `docs/planning/HANDOFF_SEQUENCE.md`. Work only on an explicitly assigned task and do not implement M1+ behavior, hosted infrastructure, UI, cloud services, or production integrations.

Use `justfile` for local commands. Keep secrets and `priv/` out of Git. The synthetic upstream is the separately owned `darizae/flowstead-sim` repository; do not vendor or copy its implementation here. Report missing approvals instead of expanding scope.
