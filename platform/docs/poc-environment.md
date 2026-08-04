# What is possible in this POC environment, and what is not

This platform exists to make prototypes reviewable: one URL, one identity, one
place that states the rules. It is **not** a staging environment and not a
lightweight production. Everything below is the honest boundary of what you can
conclude from anything you see here.

The machine-readable version of this page is
[`policy.yaml`](../policy.yaml); the portal renders it, and `platformctl`
enforces the `limits` section against every `projects/<id>.yaml` before it
deploys anything.

## Possible here

| You can | How it works | What you can conclude from it |
| --- | --- | --- |
| Walk a workflow end to end | Every prototype ships seeded data and real screens | Whether the interaction model is right |
| Switch personas globally | The portal picks a persona; the ingress injects it into every project | Whether the role split matches how the team works |
| See role-based behaviour | Each prototype enforces its own roles server-side | Whether the permission boundaries are the right ones |
| Exercise business rules | Approval thresholds, required reasons, status transitions, rollout targeting are real code | Whether the rules are correct and complete |
| Read an audit trail | Append-only tables record actor, action, reason and timestamp | Whether the evidence captured is enough for compliance to review |
| Keep state across restarts | SQLite in the pod's `$DATA_DIR`, or a small PVC when the project asks for one | Whether the data model survives a realistic sequence of actions |
| Reset to a known state | `platformctl restart <id>` replaces the pod; ephemeral data is reseeded | Repeatable demos |
| Add a prototype in a day | One `projects/<id>.yaml` and a Dockerfile; nothing else changes | Cheap experiments |
| Run prototypes side by side without them interfering | A namespace each, with its own quota and default-deny network policy | Whether one team's experiment can be trusted not to affect another's |

## Not possible here

| Not available | Why | What to do instead |
| --- | --- | --- |
| Real authentication or SSO | Identity is a header the ingress writes after asking a portal that verifies nothing. No passwords, sessions, tokens or signature checks exist | Judge the *shape* of the RBAC, never its security. Real auth is a graduation task |
| Protection against spoofing | The ingress overwrites client-supplied identity headers, but a pod reached from inside its own namespace would trust them | Reach projects through the ingress only; keep the cluster off the public internet |
| Real customer, payment or personal data | No prototype may load production exports or re-identifiable extracts. Seed data is generated | Extend the seed generators; if a question needs real data, it needs a real environment |
| Writes to production systems | No payment processor, ledger, email, messaging or third-party API calls. Money movement and customer-visible effects stop at a mocked boundary and an audit row | Mock the call, record it, and document the gap in `limitations` |
| Production-like performance or scale | One or two small pods per project, SQLite behind a process-wide lock, no pagination, caching, rate limiting or autoscaling | Treat "it feels slow with N rows" as a graduation signal, not a bug |
| Durable or authoritative data | Databases live in the pod, or at best on a 5Gi disposable volume; no migrations, no backups, gone with the namespace | Export anything you need before a redeploy |
| Secrets or credentials | There is no secret store. Config is plain env vars and committed `.env.example` files | Keep prototypes credential-free. A prototype that needs a key needs a real environment |
| Availability or support | No SLA, monitoring, alerting, on-call, or uptime target. A single small node pool, and `platformctl delete` takes a whole namespace with it | Assume anything running here can disappear |
| Security or compliance assurance | No threat model, pen test, dependency scanning, data-retention policy or DSAR handling | Do not process anything regulated |
| Multi-user concurrent use | Everyone shares one pod and one database per project; the persona is per browser, the data is not | Demo to a room, not to a department |
| Automated tests as a safety net | Coverage is smoke-level and there is no CI gate | Verify by hand before showing anything |

## Rules the platform enforces for you

A project cannot be deployed when its `projects/<id>.yaml` breaks one of these.
The check is `platform_cli/policy.py`, driven by `policy.yaml`, and it runs
before `helm` is called:

- `stage` is `poc` or `prototype` — nothing here may claim to be production.
- `data.classification` is `synthetic` or `anonymized-sample`.
- `data.persistence` is `ephemeral` or at most 5Gi — disposable only.
- the image tag is pinned; `latest`, `main` and `master` are rejected.
- no credential-shaped environment variable names — there is no secret store.
- `replicas` and `size` stay inside the platform's envelope.
- every mapped group maps to a role the project actually implements.
- at least one entry in `limitations` — every project states what it fakes.

`platformctl validate` prints the violations and `platformctl deploy` refuses to
continue, so the answer to "can I quietly point this at the real database?" is
no, in code rather than in a wiki page.

## Reading a prototype's own boundaries

Platform-wide rules are only half the story. Each project file declares its own
`capabilities` and `limitations`, rendered on the project's portal card under
"What it demonstrates / what it fakes". Read those before drawing a conclusion
from a demo: "no payment processor" and "no watchlist screening" are the sort of
thing that decides whether a review question is even answerable here.

## When a prototype outgrows this environment

That is a good outcome, and it is a rewrite of the parts this environment fakes
rather than a promotion of the same code. See
[`graduating-a-project.md`](graduating-a-project.md).
