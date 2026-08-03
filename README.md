# Devin_POC

Prototypes, and the platform that hosts them. Each prototype lives in its own
top-level folder with its own README and a `poc.yaml` manifest, and runs either
standalone or under the platform.

```bash
cd poc-platform && ./run.sh     # console on http://localhost:8080
```

| Folder | What it is |
| --- | --- |
| [`poc-platform/`](poc-platform/) | The shell: console, supervisor, gateway, mocked SSO, environment policy and docs |
| [`feature-flag-admin/`](feature-flag-admin/) | Internal feature-flag admin panel: CRUD, audit log, RBAC, %/team targeting (FastAPI + SQLite) |
| [`kyc-review-queue/`](kyc-review-queue/) | Compliance KYC review queue: case triage, decisions with required reason, audit trail, analyst/senior RBAC, escalation queue (FastAPI + SQLite) |
| [`refunds-dashboard/`](refunds-dashboard/) | Internal refunds review dashboard: queue, summary metrics, approve/deny flow, audit trail, mocked RBAC (React + Express + SQLite) |

## Start here

Documentation lives in [`poc-platform/docs/`](poc-platform/docs/) and is also
served in the console.

- **[What is possible in this POC environment, and what is not](poc-platform/docs/poc-environment.md)** —
  the boundary of what any demo here can tell you.
- [The platform contract](poc-platform/docs/platform-contract.md) — what a prototype
  must do to be hosted, and how to add a new one.
- [Target architecture](poc-platform/docs/target-architecture.md) — the in-house
  platform this POC rehearses, mapped box by box against what is actually here.
- [Next-step proposals](poc-platform/docs/roadmap.md) — the increments that would
  close those gaps, each with the question it answers.
- [Graduating a prototype](poc-platform/docs/graduating-a-poc.md) — the checklist for
  making one real.

Nothing in this repository is production software: identity is a mocked header,
all data is synthetic, and every external integration stops at a mocked boundary.
