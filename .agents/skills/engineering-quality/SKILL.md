---
name: engineering-quality
description: Apply approved engineering and security safeguards to the Flowstead scaffold.
---

# Engineering quality safeguards

Implement only an approved contract. Keep this scaffold secret-free and separate from the synthetic generator. Do not invent product behavior, dependencies, credentials, integrations or test results. Use the root `justfile`, preserve `priv/` exclusion, and report missing approvals precisely. Never publish, deploy, force-push or edit the default branch directly.
