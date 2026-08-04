# Next-step proposals

Proposals, not commitments: each closes one gap between this POC and the
[target architecture](target-architecture.md), and each is worth building only
if it changes a decision. They are independent and ordered by signal per unit of
effort.

## A. Real identity at the edge

**Gap:** the portal asserts an identity nobody verified. Everything downstream —
groups, roles, audit rows — is only as real as that assertion.

**Proposal:** replace the portal's `/auth` with oauth2-proxy in front of Entra
ID, keeping the same `X-Auth-Request-*` headers and the same ingress
annotations, and map real directory groups in each `projects/<id>.yaml`. The
portal stays as the catalog page. **No project changes** — that is the point of
the contract, and this increment is what proves it.

**Answers:** does the whole model survive contact with a real IdP, and is
"platform authenticates, project authorizes" the right split?

## B. Central append-only audit log

**Gap:** the target ships one append-only who/when/what/why log to a SIEM; here
each app keeps its own table and nothing aggregates them.

**Proposal:** ship the ingress access log (persona, host, method, path, status,
request id) plus an optional `POST /audit` from projects into one hash-chained
store in the platform namespace, with a portal tab and an export endpoint
standing in for the SIEM feed. Projects keep their own tables — the platform
becomes the aggregation point, not the only writer.

**Answers:** is an edge-level record enough for an auditor, or does every entry
need project-level context the ingress cannot see?

## C. Integration adapter layer

**Gap:** the target has one hand-written client per external system — the thing
that replaces the Power Apps connector library. Here there are no external
systems at all.

**Proposal:** mocked Core Ledger, PSP, KYC vendor and feature-flag services
deployed as their own namespaced projects, reached through one adapter interface
with idempotency keys, retries and a failure-injection switch, so "mark as
processed" and "screen this case" genuinely cross a boundary and can be made to
fail on demand. It also forces the first deliberate hole in the default-deny
network policy, which is a design decision worth making explicitly.

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

**Caveat:** done properly this means converging the prototypes onto one stack.
The platform deliberately does not require that — it deploys containers — so
this is an architectural decision about the *apps*, not a refactor, and is worth
scoping as its own piece of work.

**Answers:** the only question the business case actually turns on.

## E. Platform ops seed

**Gap:** the target owns CI, IaC, observability, SAST and SOC 2 evidence. The
IaC half exists (Bicep + Helm); nothing builds or scans anything.

**Proposal:** a GitHub Actions workflow running every test suite plus
`platformctl validate` on each PR, then building and pushing each project image
to ACR on merge and running `platformctl deploy`. That closes the last manual
step — today the image is built by hand. The rest of that box is not POC work:
it is the standing cost the target architecture makes explicit.

## Suggested order

**A + E** first: cheap, high signal, and both land inside the platform without
touching a single project — which is itself the claim being tested. Then **B**,
then **C**. Then **D**, scoped as an experiment with a measurable outcome rather
than a rewrite.
