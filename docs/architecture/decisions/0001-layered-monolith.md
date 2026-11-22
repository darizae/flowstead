# ADR 0001 — A layered monolith, not a premature package graph

**Status:** Accepted

## Context

Flowstead has one coherent plant telemetry and forecast domain. The original code spread domain decisions across HTTP handlers, PostgreSQL queries and worker modules. Reference projects demonstrate clear import direction but also contain larger package/workspace arrangements.

## Decision

Keep one installable backend Python distribution. Organize source by domain, application workflows, infrastructure adapters and HTTP/CLI interfaces. Build narrow repository interfaces and transactional units of work only where behavior requires them. Separate frontend features by ownership. Enforce domain import direction through tests/static checks.

## Consequences

Cross-layer dependencies become explicit without requiring network services or additional deployment artifacts. Compatibility shims may temporarily support existing entry points, but new code must use dedicated owners. Significant cross-layer changes require tests and updated documentation.

## Alternatives

Multiple backend microservices, a generic DI framework, and a reusable event-bus toolkit were rejected as unnecessary complexity at Flowstead's present scale.
