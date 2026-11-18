---
name: engineering-quality
description: Apply approved engineering and security safeguards to the Flowstead scaffold.
---

# Engineering quality safeguards

Implement the explicitly assigned task immediately; do not require planning-status approval, predecessor review receipts or independent reviewer certification before coding. Keep this scaffold secret-free and separate from the synthetic generator. Follow specified product behavior; resolve ordinary dependencies within the task's owning manifests/lockfiles. Do not invent credentials, integrations or test results. Use the root `justfile`, preserve `priv/` exclusion, and report missing approvals precisely. After local checks, commit and merge the task branch into local `main` without pushing. Never force-push, publish or deploy by accident; real external targets and paid/destructive actions must be specified.
