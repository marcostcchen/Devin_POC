# Target architecture, and how this POC maps onto it

The in-house platform this prototype is a rehearsal for — for what exists today,
see [architecture.md](architecture.md):

![Target architecture: an in-house Next.js/TypeScript platform with edge, auth, policy engine and audit log over a shared toolkit, thin apps, a platform data and integration layer, and platform ops](images/target-architecture.png)

**Short answer: this POC covers one box of that picture — hosting. It shows that
an independent project can be deployed onto a shared cluster by writing one
YAML file, and it deliberately implements none of the rest.**

That target's thesis is "the 3 apps are thin; the expensive part is the shared
toolkit below them — build that once, and each additional app is days, not
weeks". This POC is the opposite shape: the platform is thin — a generic Helm
chart and a CLI, with no runtime of its own — and the apps carry all of the
weight.

## Box by box

| Target | In this POC today |
| --- | --- |
| **Edge** — CDN + WAF + TLS | ingress-nginx, one hostname per project, an internal load balancer on AKS. No TLS, WAF or CDN |
| **Auth** — Okta/Entra OIDC, short-lived sessions | Nothing. Each app trusts an `X-User` header so its own roles can be demonstrated |
| **Policy engine** — RBAC/ABAC, one definition, enforced server-side | Each app enforces its own rules in its own vocabulary; there is no shared definition |
| **Audit log** — append-only, shipped to SIEM | Each app has its own audit table. No platform-level aggregation |
| **Shared toolkit** — DataTable, schema-driven forms, approval workflow, jobs | Absent. Nothing above the runtime layer is shared |
| **Apps** — thin modules, 300–600 LOC each | Three FastAPI apps of ~800–2,400 LOC. Queue table, filter bar, decision form and audit timeline are written per app |
| **Platform data** — Postgres, Redis/queue, secrets manager | One disposable SQLite per project in its `$DATA_DIR` |
| **Integration adapters** | Absent. Every payout, screening and flag read stops at seeded data |
| **Platform ops** — CI, IaC, observability, scanning, on-call | IaC only: Bicep for the cluster, Helm for everything on it |
| **Governance** | Nothing enforced. A project file is trusted as written |

## What this POC does and does not evidence

It evidences the hosting model: independent repositories, one generic chart, a
namespace and a URL per project, the same deployment locally and on AKS, and no
platform code inside any app.

It does **not** evidence the claim the business case rests on — that app #4
costs days rather than weeks — because nothing above the runtime layer is shared
yet. Nor does it evidence anything about security, isolation or compliance: the
controls that would carry those are the ones this prototype leaves out.

## Deliberate divergences (not gaps)

- **Independent projects, not one Next.js monorepo.** The point of this POC is
  that a prototype repository owes the platform a container and a health check,
  nothing more. The target's single-monorepo assumption is what makes its shared
  toolkit possible; converging on one stack is a precondition for that box, not
  a detail — and it is a decision this platform deliberately does not force.
- **`platformctl` and a hand-loaded image** instead of a build-and-deploy
  pipeline. The deployment is real Kubernetes; only the path from commit to
  image is missing.
