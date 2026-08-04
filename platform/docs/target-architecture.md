# Target architecture, and how this POC maps onto it

The in-house platform this prototype is a rehearsal for — for the current state
it is being compared against, see [architecture.md](architecture.md):

![Target architecture: an in-house Next.js/TypeScript platform with edge, auth, policy engine and audit log over a shared toolkit, thin apps, a platform data and integration layer, and platform ops](images/target-architecture.png)

**Short answer: this POC is a faithful small-scale version of the hosting half —
edge, one identity, app catalog, governance, per-app data — and it does not yet
contain the shared toolkit half, which is where the target architecture says the
cost and the value are.**

That target's thesis is "the 3 apps are thin; the expensive part is the shared
toolkit below them — build that once, and each additional app is days, not
weeks". This POC is the opposite shape: the platform is thin — a generic Helm
chart, a policy file and a CLI, with no runtime of its own — and the apps carry
all of the weight.

## Box by box

| Target | In this POC today | Verdict |
| --- | --- | --- |
| **Edge** — CDN + WAF + TLS | ingress-nginx, one hostname per project, an internal load balancer on AKS | Same shape; TLS is a cert-manager switch away, no WAF/CDN — deliberate |
| **Auth** — Okta/Entra OIDC via NextAuth, short-lived sessions | Mocked portal answering the ingress `auth-url` subrequest with `X-Auth-Request-*`; nginx overwrites spoofed copies. Apps never implement login, and swapping in oauth2-proxy + Entra ID changes no project | Same shape, mocked. Graduation item #1 |
| **Policy engine** — RBAC/ABAC, one definition, enforced server-side | Half. `platform.yaml` plus each project's `group_roles` is one definition of *who holds which role where*, but the rules themselves live in each codebase with its own vocabulary, and the platform denies nothing beyond authentication | Biggest addressable gap |
| **Audit log** — append-only, who/when/what/why, shipped to SIEM | Each app has its own audit table with actor, action, reason and timestamp. No platform-level aggregation or export | Half |
| **Shared toolkit** — DataTable, schema-driven forms, approval workflow, jobs & webhooks | Absent. Nothing above the runtime layer is shared | Missing |
| **Apps** — thin modules, 300–600 LOC each | Two FastAPI apps of ~800–2,400 LOC. Queue table, filter bar, decision form and audit timeline are still written per app | Contradicts the thesis |
| **Platform data** — App Postgres, Redis/queue, secrets manager | One disposable SQLite per project in its `$DATA_DIR`; no queue, no secret store | Simplified — deliberate |
| **Integration adapters** — one hand-written client per system | Absent. The prototypes have no external systems at all; every payout, screening and flag read stops at seeded data | Missing |
| **Platform ops** — CI, IaC, observability, SAST, pen test, SOC 2, on-call | IaC is real (Bicep for the cluster, Helm for everything on it) and Container Insights is on; no CI, no scanning, no on-call | Started |
| **Governance** (the DLP / environment-governance row of the gap panel) | `projects/<id>.yaml` + `policy.yaml`: validated before deploy, so a non-compliant project never reaches the cluster; namespace quotas and default-deny network policies enforce the rest | Ahead of expectations |

## What this POC does and does not evidence

It evidences: one identity across independent, separately deployable projects;
per-project RBAC driven by a single persona choice and a group mapping; hard
isolation between projects (namespace, quota, network policy) rather than
gentlemen's agreements; governance enforced by code rather than by a wiki page;
and that each prototype still runs standalone, with no platform code in it.

It does **not** evidence the claim the business case rests on — that app #4 costs
days rather than weeks — because nothing above the runtime layer is shared yet.
The increments that would close that gap are in [roadmap.md](roadmap.md).

## Deliberate divergences (not gaps)

- **Independent projects, not one Next.js monorepo.** The point of this POC is
  that a prototype repository owes the platform a container and a health check,
  nothing more. The target's single-monorepo assumption is what makes its shared
  toolkit possible; converging on one stack is a precondition for that box, not
  a detail — and it is a decision this platform deliberately does not force.
- **`platformctl` and a hand-loaded image** instead of a build-and-deploy
  pipeline. The deployment is real Kubernetes; only the path from commit to
  image is missing.
- **Mocked identity by design**, so reviewers can switch persona mid-demo. See
  [poc-environment.md](poc-environment.md) for the full list of what this
  environment may and may not be used to conclude.
