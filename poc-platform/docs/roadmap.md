# Next-step proposals

Proposals, not commitments: each closes one gap between this POC and the
[target architecture](target-architecture.md), and each is worth building only
if it changes a decision. They are independent and ordered by signal per unit of
effort.

## A. Central policy engine — one definition, enforced at the gateway

**Gap:** the target has one RBAC/ABAC definition enforced server-side; here the
rules live in three codebases with three vocabularies and the gateway denies
nothing.

**Proposal:** a `permissions.yaml` mapping roles to capabilities
(`flags:write`, `kyc:view_escalated`, `refunds:approve`,
`refunds:approve_over_threshold`, …) plus route rules per app. The gateway
evaluates them before proxying, answers 403 with the rule that denied the
request, and injects `X-Platform-Permissions`; apps keep their own checks as
defence in depth. The refunds amount threshold moves out of an `if` in the
service and becomes an attribute rule, which is the ABAC half of that box.

**Answers:** can one definition express the three apps' rules without becoming a
lowest common denominator? Where does app-specific logic legitimately stay?

## B. Central append-only audit log

**Gap:** the target ships one append-only who/when/what/why log to a SIEM; here
each app keeps its own table and nothing aggregates them.

**Proposal:** `POST /api/platform/audit` plus automatic capture of every mutating
proxied request (persona, app, action, reason, request id, timestamp) into a
hash-chained JSONL file; an **Audit** tab in the console with filters, and an
export endpoint standing in for the SIEM feed. Apps keep their own tables — the
platform becomes the aggregation point, not the only writer.

**Answers:** is a gateway-level record enough for an auditor, or does every
entry need app-level context the proxy cannot see?

## C. Integration adapter layer

**Gap:** the target has one hand-written client per external system — the thing
that replaces the Power Apps connector library. Here there are no external
systems at all.

**Proposal:** mocked Core Ledger, PSP, KYC vendor and feature-flag services
behind one adapter interface with idempotency keys, retries and a
failure-injection switch in the console, so "mark as processed" and "screen this
case" genuinely cross a boundary and can be made to fail on demand.

**Answers:** how much of each app is really integration plumbing, and what does
an ops person see when a downstream system is down?

## D. The toolkit thesis, tested honestly

**Gap:** the economics ("~5–10 eng-weeks for 3 apps + toolkit, then days per
app") rest entirely on the shared toolkit, and nothing in this repository shares
anything above the runtime layer.

**Proposal:** extract a small shared package — DataTable with server-side filter
and sort, schema-driven form, decision panel with required reason, audit
timeline — rebuild one existing screen on it, then scaffold a fourth thin app
from it and measure the result against the 300–600 LOC claim.

**Caveat:** done properly this means converging the three prototypes onto one
stack, because a shared toolkit across FastAPI+React, static JS and Express is
either duplicated three times or reduced to an API contract. That is a
deliberate architectural decision, not a refactor — worth scoping as its own
piece of work.

**Answers:** the only question the business case actually turns on.

## E. Platform ops seed

**Gap:** the target owns CI, IaC, observability, SAST and SOC 2 evidence; this
repository has no CI at all.

**Proposal:** a GitHub Actions workflow running the four test suites plus lint
and typecheck on every PR. The rest of that box is not POC work — it is the
standing cost the target architecture makes explicit, and pretending to
prototype it would be misleading.

## Suggested order

**A + B + E** first: cheap, high signal, and all three land inside the platform
without touching the prototypes. Then **C**. Then **D**, scoped as an experiment
with a measurable outcome rather than a rewrite.
