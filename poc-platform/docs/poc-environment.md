# What is possible in this POC environment, and what is not

This platform exists to make prototypes reviewable: one URL, one identity, one
place that states the rules. It is **not** a staging environment and not a
lightweight production. Everything below is the honest boundary of what you can
conclude from anything you see here.

The machine-readable version of this page is
[`policy.yaml`](../policy.yaml); the console renders it, and the registry
enforces the `limits` section against every `poc.yaml` at startup.

## Possible here

| You can | How it works | What you can conclude from it |
| --- | --- | --- |
| Walk a workflow end to end | Every prototype ships seeded data and real screens | Whether the interaction model is right |
| Switch personas globally | The console picks a persona; the gateway injects it into every app | Whether the role split matches how the team works |
| See role-based behaviour | Each prototype enforces its own roles server-side | Whether the permission boundaries are the right ones |
| Exercise business rules | Approval thresholds, required reasons, status transitions, rollout targeting are real code | Whether the rules are correct and complete |
| Read an audit trail | Append-only tables record actor, action, reason and timestamp | Whether the evidence captured is enough for compliance to review |
| Keep state across restarts | Local SQLite per prototype, under `poc-platform/.data/` | Whether the data model survives a realistic sequence of actions |
| Reset to a known state | `poc-platform/reset.sh` deletes every database and log | Repeatable demos |
| Add a prototype in a day | Drop a `poc.yaml` next to a `run.sh`; the console picks it up | Cheap experiments |
| Let prototypes call each other | Through the gateway, with platform identity headers | Whether an integration is worth building properly |

## Not possible here

| Not available | Why | What to do instead |
| --- | --- | --- |
| Real authentication or SSO | Identity is a header the gateway writes and every app trusts. No passwords, sessions, tokens or signature checks exist | Judge the *shape* of the RBAC, never its security. Real auth is a graduation task |
| Protection against spoofing | An app reached directly on its own port accepts whatever identity headers a caller sends | Never expose a prototype outside the machine it runs on |
| Real customer, payment or personal data | No prototype may load production exports or re-identifiable extracts. Seed data is generated | Extend the seed generators; if a question needs real data, it needs a real environment |
| Writes to production systems | No payment processor, ledger, email, messaging or third-party API calls. Money movement and customer-visible effects stop at a mocked boundary and an audit row | Mock the call, record it, and document the gap in `limitations` |
| Production-like performance or scale | One process per app, SQLite behind a process-wide lock, no pagination, caching, rate limiting or horizontal scale | Treat "it feels slow with N rows" as a graduation signal, not a bug |
| Durable or authoritative data | Databases live in `poc-platform/.data/`, are deleted by `reset.sh`, have no migrations and no backups | Export anything you need before a reset |
| Secrets or credentials | There is no secret store. Config is plain env vars and committed `.env.example` files | Keep prototypes credential-free. A prototype that needs a key needs a real environment |
| Availability or support | No SLA, monitoring, alerting, on-call, or uptime target. The gateway kills every child when it stops | Assume anything running here can disappear |
| Security or compliance assurance | No threat model, pen test, dependency scanning, data-retention policy or DSAR handling | Do not process anything regulated |
| Multi-user concurrent use | Everyone who opens the console shares the same processes and databases; the persona is per browser, the data is not | Demo to a room, not to a department |
| Automated tests as a safety net | Coverage is smoke-level and there is no CI gate | Verify by hand before showing anything |

## Rules the platform enforces for you

A prototype cannot be started from the console when its `poc.yaml` breaks one of
these. The check is `platform_core/policy.py`, driven by `policy.yaml`:

- `stage` is `poc` or `prototype` — nothing here may claim to be production.
- `data.classification` is `synthetic` or `anonymized-sample`.
- `data.store` is `sqlite`, `memory` or `file` — local and disposable only.
- `identity.mode` is `platform-headers` — mocked identity, always.
- At least one entry in `limitations` — every prototype states what it fakes.

Violations are shown on the app's card in the console and the start button is
disabled, so the answer to "can I quietly point this at the real database?" is
no, in code rather than in a wiki page.

## Reading a prototype's own boundaries

Platform-wide rules are only half the story. Each `poc.yaml` declares its own
`capabilities` and `limitations`, rendered on the app's console card under
"What it demonstrates / what it fakes". Read those before drawing a conclusion
from a demo: "no payment processor" and "no watchlist screening" are the sort of
thing that decides whether a review question is even answerable here.

## When a prototype outgrows this environment

That is a good outcome, and it is a rewrite of the parts this environment fakes
rather than a promotion of the same code. See
[`graduating-a-poc.md`](graduating-a-poc.md).
