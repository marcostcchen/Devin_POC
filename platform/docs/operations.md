# Operating the platform

`platformctl` is the whole interface. It is a thin wrapper over `helm`,
`kubectl` and `docker` with no state of its own: the project files are the
source of truth and the cluster holds everything else.

## Commands

| Command | What it does |
| --- | --- |
| `list` | Every project, its namespace, its URL and whether it passes policy |
| `validate [project…]` | Check project files against `policy.yaml`; exit 1 on a violation |
| `render [project…]` `--portal` | Print the manifests Helm would apply, without touching the cluster |
| `deploy [project…]` `--wait` `--timeout` | `helm upgrade --install`, creating the namespace and everything in it |
| `delete <project…>` | Uninstall the release and delete the namespace with it |
| `restart <project…>` | Roll the pods, which resets ephemeral data |
| `status` | Which pod is serving each project, and where |
| `build [project…]` `--portal` `--load` `--kind-cluster` | `docker build` from each project's `repo`, optionally `kind load` |
| `bootstrap --target local\|aks` | Install ingress-nginx and the portal |
| `new <id>` | Scaffold `projects/<id>.yaml` from the template |

With no project argument, the commands that accept a list act on every project.
Release state lives in the platform namespace, so `helm list -n poc-platform`
shows every project alongside the portal.

## A day of work

```bash
./platformctl new payouts-review          # scaffold, then edit the file
./platformctl validate payouts-review     # policy first — it runs again on deploy
./platformctl render payouts-review | less
./platformctl build payouts-review --load # local only; on AKS, push to the ACR
./platformctl deploy payouts-review --wait
./platformctl status
```

Reading a project's logs, shell and events is plain `kubectl` against its
namespace:

```bash
kubectl -n poc-payouts-review logs -l app.kubernetes.io/name=payouts-review -f
kubectl -n poc-payouts-review get events --sort-by=.lastTimestamp
kubectl -n poc-payouts-review describe pod -l app.kubernetes.io/name=payouts-review
```

## Deploying to AKS instead of kind

Only three things differ, all of them in configuration:

1. `platform.yaml` — `registry` set to the ACR login server, `domain` set to the
   real DNS zone, and the public port dropped;
2. `bootstrap/ingress-nginx.aks.yaml` — used by `bootstrap --target aks`;
3. images are pushed rather than `kind load`ed:

```bash
az acr login --name <registry>
docker tag poc/kyc-review-queue:0.1.0 <registry>.azurecr.io/poc/kyc-review-queue:0.1.0
docker push <registry>.azurecr.io/poc/kyc-review-queue:0.1.0
```

No pull secret is created anywhere: `infra/aks/main.bicep` grants `AcrPull` to
the cluster's kubelet identity instead.

## Things that will bite you

**A rebuilt image with the same tag does not reach a running pod.** Tags are
pinned, so `build --load` followed by `deploy` produces an unchanged pod spec
and Kubernetes has no reason to restart anything. Bump the tag in the project
file (right, and what the platform is designed for), or during local
iteration:

```bash
./platformctl build my-project --load && ./platformctl restart my-project
```

**A project cannot reach anything by default.** Egress is deny-all apart from
DNS, so a project that starts calling another service will simply time out.
That is the isolation working; opening a path is a deliberate change to the
chart's NetworkPolicies, not a configuration accident.

**`*.localhost` only resolves in a browser.** `curl` needs
`--resolve kyc.poc.localhost:8080:127.0.0.1`, or `/etc/hosts` entries.

**Everything is HTTP locally.** The kind cluster publishes 8080/8443 from the
control-plane node; TLS is an AKS-only concern (`platform.tls`).

## When something is not serving

| Symptom | Usual cause |
| --- | --- |
| `deploy` fails with `namespaces "poc-platform" not found` | `bootstrap` has not run in this cluster |
| The URL 404s from nginx | No Ingress yet — the release did not deploy, or the host does not match `platform.yaml` |
| The URL redirects to the portal forever | The portal is down, or the session cookie's domain does not match the platform domain |
| The URL 503s | The pod is not ready: check the health path, then `kubectl -n poc-<id> logs` |
| The pod is `CrashLoopBackOff` right after start | Usually the read-only root filesystem or a non-`/data` write; check the container's own paths |
| `Pending` pods with a quota message | The project asked for more than its `ResourceQuota`: raise `size`/`replicas` in the project file, within `policy.yaml`'s ceilings |

## Tearing down

```bash
./platformctl delete kyc-review-queue     # one project, namespace and all
kind delete cluster --name poc-platform   # the whole local environment
```
