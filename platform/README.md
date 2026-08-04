# POC Platform

A Kubernetes namespace, a hostname and an identity for every prototype — and
nothing else. Projects are ordinary containers in their own repositories; the
platform only decides *where* they run and *who* reaches them.

Onboarding a project is one file:

```bash
./platformctl new my-project      # writes projects/my-project.yaml from the template
$EDITOR projects/my-project.yaml  # image, port, roles, size
./platformctl deploy my-project
```

No platform code, no chart, no pipeline is edited to add a project. The same
`projects/*.yaml` deploys to the local cluster and to AKS.

## Layout

| Path | What it is |
| --- | --- |
| `platform.yaml` | Cluster-wide settings: domain, registry, sizes, the mocked directory |
| `policy.yaml` | What a project is allowed to ask for; enforced before every deploy |
| `projects/*.yaml` | One file per project — the entire per-project configuration |
| `charts/poc-app` | The single generic chart every project is deployed with |
| `charts/poc-portal` | The catalog page and the mocked sign-in |
| `portal/` | The portal service (FastAPI); replaced by oauth2-proxy in a real deployment |
| `platform_cli/`, `platformctl` | The CLI: validate, render, build, deploy, delete, status |
| `bootstrap/` | ingress-nginx values for local and AKS, plus the platform namespace |
| `infra/aks/` | Bicep for the cluster, the registry and the logs |
| `local/kind-cluster.yaml` | The local cluster, shaped like the AKS one |

## Run it locally

Needs docker, kind, kubectl and helm.

```bash
kind create cluster --config local/kind-cluster.yaml
./platformctl bootstrap --target local     # ingress-nginx + the portal
./platformctl build --load                 # build every image, load it into kind
./platformctl deploy --wait
```

Then open <http://portal.poc.localhost:8080> — `*.localhost` resolves to
127.0.0.1 in browsers, so there is nothing to add to `/etc/hosts`. Sign in as a
persona and follow the links: <http://kyc.poc.localhost:8080>,
<http://flags.poc.localhost:8080>, <http://refunds.poc.localhost:8080>.

```bash
./platformctl status                       # what is running, per project
./platformctl delete kyc-review-queue      # removes the namespace with it
```

The full command reference, the day-2 commands and the failure modes are in
[docs/operations.md](docs/operations.md).

## Deploy it to AKS

```bash
RESOURCE_GROUP=poc-platform-rg infra/aks/deploy.sh   # cluster + ACR + logs
# point platform.yaml at the ACR login server and the internal DNS zone, then
./platformctl bootstrap --target aks
./platformctl deploy
```

The only differences from local are in `platform.yaml` (registry, domain, port,
TLS) and in `bootstrap/ingress-nginx.aks.yaml` (an internal Azure load
balancer). The chart, the project files and the namespaces are identical.

## What a project has to do

[docs/project-contract.md](docs/project-contract.md) — in short: listen on
`$PORT`, answer the health path, write only to `$DATA_DIR`, and if
`AUTH_MODE=proxy-headers` trust the `X-Auth-Request-*` headers the ingress
injects. A project never imports platform code and runs unchanged on a laptop.

## What the platform enforces

`policy.yaml` is checked by `platformctl validate` and again on every deploy: no
production stage, no unpinned image tags, no real data classifications, no
credential-shaped environment variables, no unbounded replicas or storage, roles
that actually exist, and at least one declared limitation. A namespace it
creates gets a resource quota, a limit range, Pod Security Admission
`restricted`, and default-deny NetworkPolicies.

See [docs/architecture.md](docs/architecture.md) for how that fits together, and
[docs/poc-environment.md](docs/poc-environment.md) for what conclusions this
environment does and does not support. [docs/](docs/) indexes the rest.

## Tests

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m pytest tests    # policy, rendering, and the chart itself
./platformctl validate                # the real projects, against policy.yaml

cd portal && python3 -m venv .venv && ./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/python -m pytest tests    # the auth subrequest and the catalog
```

The chart tests shell out to `helm template`, so helm has to be on `$PATH`; no
cluster is needed for any of them.
