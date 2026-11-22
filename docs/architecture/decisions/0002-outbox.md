# ADR 0002 — Durable commands and transactional outbox

**Status:** Accepted (pre-existing behavior retained during refactor)

## Context

Forecast requests cross PostgreSQL and NATS/JetStream, which cannot participate in one shared database transaction. Publishing directly in an HTTP request risks losing messages or creating duplicate work under network failure.

## Decision

Atomically persist a forecast command and its outbox message in PostgreSQL. Dispatch to JetStream separately. Consumers must process idempotently, preserve transactional boundaries and retain bounded retry/dead-letter behavior. Forecast mathematics stays deterministic and side-effect-free.

## Consequences

Duplicate delivery and recovery are expected. Worker tests must cover replay, concurrency and failure transitions against disposable PostgreSQL and JetStream, not only unit mocks. HTTP handlers must not bypass the outbox for convenience.
