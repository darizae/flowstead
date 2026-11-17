# 001 — repository initialization

**Repository:** `darizae/flowstead`  
**Base:** `main`  

## Authorization and scope

Owner authorization the accepted repository initialization/the repository initialization gate permits exactly this private application scaffold, default `main`, and its first secret-free push. Preflight must confirm the exact remote is absent; do not reuse, rename, overwrite, force-push, or create another repository.

## Read set

`AGENTS.md`, `README.md`, `justfile`, `.gitignore`, `docs/planning/IMPLEMENTATION_SPEC.md`, `docs/planning/HANDOFF_SEQUENCE.md`, and `.agents/skills/github-repository-creation/SKILL.md`.

## Acceptance

Verify authenticated `gh`, clean local status, `main`, exact private remote, matching origin, published initial SHA, and no secrets or `priv/` content in the commit. Run `just --list` locally. No application implementation is in scope.
