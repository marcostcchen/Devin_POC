# Devin_POC

Prototypes, and the Kubernetes platform that deploys them. Each prototype is an
ordinary container in its own folder — it depends on its own stack and on
nothing in `platform/`. The platform gives it a namespace and a hostname.

```bash
cd platform
./platformctl bootstrap --target local   # kind cluster + ingress
./platformctl build --load && ./platformctl deploy --wait
# http://kyc.poc.localhost:8080, http://flags.poc.localhost:8080, http://refunds.poc.localhost:8080
```

The same commands run against AKS; only `platform.yaml` differs.

| Folder | What it is |
| --- | --- |
| [`platform/`](platform/) | The platform: one generic Helm chart, one YAML file per project, `platformctl`, and the AKS Bicep |
| [`feature-flag-admin/`](feature-flag-admin/) | Internal feature-flag admin panel: CRUD, audit log, RBAC, %/team targeting (FastAPI + SQLite) |
| [`kyc-review-queue/`](kyc-review-queue/) | Compliance KYC review queue: case triage, decisions with required reason, audit trail, analyst/senior RBAC, escalation queue (FastAPI + SQLite) |
| [`refunds-dashboard/`](refunds-dashboard/) | Refund review dashboard: queue and summary metrics, approve/deny with a required reason, a finance approval threshold, mocked payouts, audit trail (FastAPI + SQLite) |

## Adding a project

```bash
cd platform && ./platformctl new my-project   # then edit projects/my-project.yaml
./platformctl deploy my-project
```

That is the whole onboarding: no platform code, no chart and no pipeline is
touched. All a project has to do is listen on `$PORT`, answer `GET /healthz`,
and write only under `$DATA_DIR`.

## Start here

- [Architecture](platform/docs/architecture.md) — what actually runs, how local
  and AKS stay identical, and what the prototype deliberately leaves out.
- [Business overview](platform/docs/business-view.md) — the same thing without
  the Kubernetes vocabulary.
- [Target architecture](platform/docs/target-architecture.md) — the in-house
  platform this POC rehearses, mapped box by box against what is actually here.

Nothing in this repository is production software: there is no authentication,
all data is synthetic, and every external integration stops at a mocked
boundary.
