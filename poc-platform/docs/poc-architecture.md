# Current POC architecture

What is actually running in this repository today, on one laptop.

![Current POC architecture: reviewers on the left, the FastAPI gateway, mocked SSO, policy and supervisor over three prototypes with per-app SQLite in the middle, unconnected external systems on the right, and the list of things this POC cannot be used to conclude](images/poc-architecture.png)

Green is real code in this repository, amber is deliberately mocked, red is
absent. The diagram is generated from
[`images/poc-architecture.html`](images/poc-architecture.html).

## The request path

```
browser → :8080 gateway → strip client X-Platform-* headers
                        → inject persona + this app's role
                        → 127.0.0.1:<app port>/apps/<id>/…   (prefix kept)
```

Everything reviewers touch is one origin. Each prototype is a child process the
supervisor starts, health-checks and tails logs from; a prototype whose
`poc.yaml` breaks [`policy.yaml`](../policy.yaml) cannot be started at all.

## What each layer really is

| Layer | Today |
| --- | --- |
| Edge | FastAPI/Uvicorn on `:8080`, no TLS, no WAF, no CDN |
| Identity | Persona picker. The gateway asserts `X-Platform-User` / `X-Platform-Role`; nothing is verified |
| Authorisation | One map of persona → per-app role in `platform.yaml`; the rules themselves live in each app, in three vocabularies |
| Governance | `poc.yaml` validated against `policy.yaml` on load — enforced, not documented |
| Apps | Three full prototypes on three stacks, ~840 / 2,400 / 3,200 LOC |
| Shared toolkit | None. Queue table, filter bar, decision form and audit timeline exist three times |
| Data | One disposable SQLite per app under `$PLATFORM_DATA_DIR`, synthetic seed, per-app audit table |
| Integrations | None. Every payout, screening and ledger call stops at seeded data |
| Ops | No CI, no IaC, no monitoring, no container, no deploy |

## How to read it

This diagram is the *current* state. The end state it is a rehearsal for — and
the box-by-box distance between the two — is in
[target-architecture.md](target-architecture.md); the increments that close the
distance are in [roadmap.md](roadmap.md).

For the full statement of what may and may not be concluded from a demo here,
see [poc-environment.md](poc-environment.md).
