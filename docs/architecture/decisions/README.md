# Architecture decision records

ADRs record consequential design choices and the invariants that should survive future refactors. Use numbered Markdown files with Context, Decision, Consequences, and Alternatives. Proposed changes should create a successor ADR rather than silently overwrite history.

- [0001: Keep a layered single backend distribution](0001-layered-monolith.md)
- [0002: Preserve transactional outbox and idempotent JetStream processing](0002-outbox.md)
- [0003: SQL-enforced Plant authorization and provenance](0003-security-provenance.md)
