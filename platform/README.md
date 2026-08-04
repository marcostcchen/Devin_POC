# POC Platform

A Kubernetes namespace and a hostname for every prototype, and nothing else.
Projects are ordinary containers in their own repositories; the platform only
decides *where* they run and *what URL* they answer on.

Onboarding a project is one file:

```bash
./platformctl new my-project      # writes projects/my-project.yaml from the template
$EDITOR projects/my-project.yaml  # image, hostname, and anything the app needs
./platformctl deploy my-project
```

No platform code, no chart and no pipeline is edited to add a project. The same
`projects/*.yaml` deploys to the local cluster and to AKS.

## Layout

| Path | What it is |
| --- | --- |
| `platform.yaml` | The cluster: domain, namespace prefix, registry, ingress |
| `projects/*.yaml` | One file per project — the entire per-project configuration |
| `charts/poc-app` | The single generic chart every project is deployed with |
| `platform_cli/`, `platformctl` | The CLI: build, deploy, status, delete |
| `bootstrap/` | ingress-nginx values, for the local cluster and for AKS |
| `infra/aks/` | Bicep for the cluster and its registry |
| `local/kind-cluster.yaml` | The local cluster, shaped like the AKS one |

## Run it locally

Needs docker, kind, kubectl and helm.

```bash
./platformctl bootstrap --target local   # creates the kind cluster + ingress-nginx
./platformctl build --load               # build every image, load it into kind
./platformctl deploy --wait
```

Then open <http://kyc.poc.localhost:8080>, <http://flags.poc.localhost:8080> or
<http://refunds.poc.localhost:8080> — `*.localhost` resolves to 127.0.0.1 in
browsers, so there is nothing to add to `/etc/hosts`.

```bash
./platformctl list                       # every project, its namespace and URL
./platformctl status                     # what is actually running
./platformctl render kyc-review-queue    # the manifests, without deploying them
./platformctl delete kyc-review-queue    # removes the namespace with it
```

## Deploy it to AKS

```bash
RESOURCE_GROUP=poc-platform-rg infra/aks/deploy.sh   # cluster + ACR
# point platform.yaml at the ACR login server and the DNS zone, then
./platformctl bootstrap --target aks
./platformctl deploy
```

The only differences from local are in `platform.yaml` (registry, domain, port)
and in `bootstrap/ingress-nginx.aks.yaml` (an internal Azure load balancer). The
chart, the project files and the namespaces are identical. The Bicep has not
been run against a real subscription.

## What a project has to do

Ship a container that listens on `$PORT`, answers `GET /healthz` while it is
alive, and writes only under `$DATA_DIR`. That is the whole contract: a project
never imports platform code, and it runs unchanged with `docker run` on a
laptop.

## What this prototype leaves out

Authentication, authorization between projects, quotas, network policy, secrets
and TLS. Each app fakes its own users with an `X-User` header so its role
behaviour can be demonstrated; nothing verifies who the caller is. This is a
prototype for the deployment model only.

## Docs

| Document | What it answers |
| --- | --- |
| [docs/operations-guide.md](docs/operations-guide.md) | How to set up, operate, troubleshoot, and onboard an application |
| [docs/in-house-solution-prototype.md](docs/in-house-solution-prototype.md) | What the POC proves and what an in-house production solution requires |
| [docs/running-multiple-applications.md](docs/running-multiple-applications.md) | How Kubernetes schedules and routes multiple applications |
| [docs/architecture.md](docs/architecture.md) | What runs today, and what is deliberately missing |
| [docs/target-architecture.md](docs/target-architecture.md) | What we are aiming at, and what it assumes |
| [docs/gap-analysis.md](docs/gap-analysis.md) | The difference between the two, box by box |
| [docs/migration-plan.md](docs/migration-plan.md) | How to close it, in what order, and where to stop |
| [docs/business-view.md](docs/business-view.md) | The same picture without the Kubernetes vocabulary |

## Tests

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m pytest tests
```

The chart tests shell out to `helm template`, so helm has to be on `$PATH`; no
cluster is needed.
