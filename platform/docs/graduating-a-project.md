# Graduating a prototype

The checklist for turning something on this platform into something a team can
depend on. Every item exists because the POC environment fakes it; see
[what is possible here](poc-environment.md).

Graduation is a **rewrite of the faked parts**, not a promotion of the same
deployment onto a bigger cluster. Expect the workflow code, the UI and the
container to survive — a project already listens on `$PORT`, reads its identity
from headers and writes to one directory — and expect identity, storage and
every integration boundary to be replaced.

## Identity and access

- [ ] Real authentication (OIDC/SSO). Trusted headers are acceptable only behind
      a proxy that authenticates and overwrites them, and never between services.
- [ ] Roles derived from a directory group, enforced server-side per request.
- [ ] Segregation of duties where money or compliance is involved (the requester
      cannot approve their own case).
- [ ] Access logging on anything that reads personal data.

## Data

- [ ] Postgres (or equivalent) instead of SQLite, with migrations checked in.
- [ ] Amounts as integer minor units with an explicit currency.
- [ ] Real data classification, retention and deletion policy; DSAR handling.
- [ ] Encryption at rest and in transit; secrets in a secret manager.
- [ ] Backups, and a restore that someone has actually tested.

## Integrations

- [ ] Replace each mocked boundary with an idempotent, retrying client.
- [ ] Webhook or reconciliation loop for anything asynchronous.
- [ ] An exception report for mismatches, owned by a named team.

## Correctness

- [ ] Unit tests for the business rules, integration tests for the API,
      end-to-end tests for the golden paths - all gated in CI.
- [ ] Explicit state machine for statuses, with transitions tested.
- [ ] Concurrency control (optimistic locking) instead of read-then-write.

## Operations

- [ ] Deployment pipeline from commit to image to cluster, with rollback; the
      platform's `platformctl build && platformctl deploy` is a human, not a
      pipeline.
- [ ] Resource requests and limits sized from measurement rather than from a
      `size: small` shorthand.
- [ ] An egress policy written for the integrations the service actually needs,
      instead of the platform's default-deny.
- [ ] Structured logs, metrics, alerts and an owner to page.
- [ ] Pagination, indexing and load testing at the expected volume.
- [ ] Rate limits and abuse protection on anything user-facing.

## Compliance and audit

- [ ] Tamper-evident audit log (append-only storage, hash chain or WORM) with a
      retention period the business has signed off.
- [ ] Before/after values captured for every state change.
- [ ] Threat model, dependency scanning, and a security review.

## The exit criteria

A prototype leaves this platform when it stops being a prototype: it has an
owning team, a pipeline, an on-call rotation and tests. Until then it stays
here, with its limitations written down in its `projects/<id>.yaml`.
