# Devin_POC

Prototypes, and the Kubernetes platform that deploys them. Each prototype is an
ordinary container in its own folder — it depends on its own stack and on
nothing in `platform/`. The platform gives it a namespace, a hostname and an
identity.

```bash
cd platform
kind create cluster --config local/kind-cluster.yaml
./platformctl bootstrap --target local && ./platformctl build --load && ./platformctl deploy --wait
# portal on http://portal.poc.localhost:8080
```

The same commands run against AKS; only `platform.yaml` differs.

| Folder | What it is |
| --- | --- |
| [`platform/`](platform/) | The platform: one generic Helm chart, one YAML file per project, `platformctl`, the portal and the AKS Bicep |
| [`feature-flag-admin/`](feature-flag-admin/) | Internal feature-flag admin panel: CRUD, audit log, RBAC, %/team targeting (FastAPI + SQLite) |
| [`kyc-review-queue/`](kyc-review-queue/) | Compliance KYC review queue: case triage, decisions with required reason, audit trail, analyst/senior RBAC, escalation queue (FastAPI + SQLite) |
| [`refunds-dashboard/`](refunds-dashboard/) | Refund review dashboard: queue and summary metrics, approve/deny with a required reason, a finance approval threshold, mocked payouts, audit trail (FastAPI + SQLite) |

## Adding a project

```bash
cd platform && ./platformctl new my-project   # then edit projects/my-project.yaml
./platformctl deploy my-project
```

That is the whole onboarding: no platform code, no chart and no pipeline is
touched. What the project itself has to do is in
[the project contract](platform/docs/project-contract.md) — listen on `$PORT`,
answer a health path, write only to `$DATA_DIR`, and read identity from
`X-Auth-Request-*` when it is deployed behind the platform.

## Start here

- **[What is possible in this POC environment, and what is not](platform/docs/poc-environment.md)** —
  the boundary of what any demo here can tell you.
- [Architecture](platform/docs/architecture.md) — what actually runs, how local
  and AKS stay identical, and how far the isolation goes.
- [The project contract](platform/docs/project-contract.md) — what a prototype
  must do to be deployable, and how to add a new one.
- [Operating the platform](platform/docs/operations.md) — the `platformctl`
  reference, the AKS differences, and what to check when something is not
  serving.
- [Target architecture](platform/docs/target-architecture.md) — the in-house
  platform this POC rehearses, mapped box by box against what is actually here.
- [Next-step proposals](platform/docs/roadmap.md) — the increments that would
  close those gaps, each with the question it answers.
- [Graduating a project](platform/docs/graduating-a-project.md) — the checklist
  for making one real.

Nothing in this repository is production software: identity is asserted by a
mocked portal, all data is synthetic, and every external integration stops at a
mocked boundary.
