# Platform operations guide

This guide covers the complete lifecycle of an application on the POC
platform: preparing a local cluster, deploying and inspecting applications,
onboarding a new application, updating it, and removing it.

All commands in this guide run from the `platform/` directory:

```bash
cd platform
```

## 1. Understand the operating model

The platform has no long-running control service. `platformctl` reads
`platform.yaml` and `projects/*.yaml`, generates values for the shared Helm
chart, and invokes Docker, kind, Helm, and kubectl.

Each application is deployed as one Helm release in its own Kubernetes
namespace. The shared chart creates a Deployment, Service, and Ingress.

```text
application folder --docker build--> image
project YAML + platform YAML --platformctl/Helm--> Kubernetes resources
image + Kubernetes resources --> running application
```

The application folder is used only while building the image. Kubernetes runs
the image and has no direct connection to the source folder.

## 2. Prerequisites

Local operation requires:

- Python 3
- Docker
- kind
- kubectl
- Helm

Verify the tools before bootstrapping the platform:

```bash
python3 --version
docker version
kind version
kubectl version --client
helm version
```

Docker must be running. `platformctl` creates `platform/.venv` and installs its
Python requirements automatically the first time it runs.

## 3. Start the local platform

Create the kind cluster and install ingress-nginx:

```bash
./platformctl bootstrap --target local
```

Build every configured application and load the images into kind:

```bash
./platformctl build --load
```

Deploy every configured application and wait for readiness:

```bash
./platformctl deploy --wait
```

List their namespaces and URLs:

```bash
./platformctl list
```

The initial applications are available at:

- <http://flags.poc.localhost:8080>
- <http://kyc.poc.localhost:8080>
- <http://refunds.poc.localhost:8080>

The `*.localhost` names resolve to `127.0.0.1` automatically; no hosts-file
entry is required.

## 4. Daily application workflow

After changing an application's source code, rebuild its image, load it into
kind, and deploy the release:

```bash
./platformctl build feature-flag-admin --load
./platformctl deploy feature-flag-admin --wait
```

The development images currently use fixed tags and the chart uses
`imagePullPolicy: IfNotPresent`. If the Deployment specification did not
change, Kubernetes might leave the existing pod running after a same-tag image
was rebuilt. Recreate the pod to use the newly loaded image:

```bash
kubectl rollout restart deployment/feature-flag-admin \
  --namespace poc-feature-flag-admin
kubectl rollout status deployment/feature-flag-admin \
  --namespace poc-feature-flag-admin
```

For traceable deployments, assign a new image tag in the project's YAML file,
build it, and deploy it instead of reusing a tag.

## 5. Inspect applications

Show all configured projects, whether deployed or not:

```bash
./platformctl list
```

Show the current pod state for every project:

```bash
./platformctl status
```

Render the Kubernetes manifests without changing the cluster:

```bash
./platformctl render feature-flag-admin
```

Inspect one deployed release and its resources:

```bash
helm status feature-flag-admin \
  --namespace poc-feature-flag-admin
kubectl get deployment,service,ingress,pod \
  --namespace poc-feature-flag-admin
```

Read logs or follow them while testing:

```bash
kubectl logs deployment/feature-flag-admin \
  --namespace poc-feature-flag-admin
kubectl logs --follow deployment/feature-flag-admin \
  --namespace poc-feature-flag-admin
```

Inspect the effective Helm values and generated manifests:

```bash
helm get values feature-flag-admin \
  --namespace poc-feature-flag-admin
helm get manifest feature-flag-admin \
  --namespace poc-feature-flag-admin
```

## 6. Create and onboard a new application

### 6.1 Implement the container contract

The application may use any language or framework. Its container must:

1. Listen on the port in `$PORT`.
2. Return a successful response from `GET /healthz`, unless `health_path` is
   overridden in its project configuration.
3. Write runtime data only below `$DATA_DIR`.
4. Include a Dockerfile at the root of its build context.

A minimal Python example could use this health endpoint:

```python
import os

from fastapi import FastAPI

app = FastAPI()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def index() -> dict[str, str]:
    return {"message": "Hello from the platform"}


port = int(os.environ.get("PORT", "8000"))
data_dir = os.environ.get("DATA_DIR", "/data")
```

The server command in the image must bind to `0.0.0.0`, not only `127.0.0.1`.
For example:

```dockerfile
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

### 6.2 Scaffold the platform configuration

Assuming the application folder is a sibling of `platform/`, create its project
configuration:

```bash
./platformctl new inventory-app
```

Edit `projects/inventory-app.yaml`:

```yaml
id: inventory-app
name: Inventory App
summary: View and update product inventory.
repo: ../inventory-app

image: poc/inventory-app:0.1.0
host: inventory

port: 8000
health_path: /healthz
replicas: 1
env:
  APP_ENV: local
```

The fields mean:

| Field | Purpose |
| --- | --- |
| `id` | Helm release name and the suffix of the namespace |
| `name` | Human-readable name printed after deployment |
| `summary` | Description for people reading the configuration |
| `repo` | Local Docker build context, resolved from `platform/` |
| `image` | Image tag built by Docker and run by Kubernetes |
| `host` | Hostname prefix below the domain in `platform.yaml` |
| `port` | Container port supplied through `$PORT` |
| `health_path` | Kubernetes readiness endpoint |
| `replicas` | Number of application pods |
| `env` | Additional non-secret environment variables |

Do not store passwords, tokens, or other secrets in `env`; this POC does not
provide secret management.

### 6.3 Validate, build, and deploy

Render the manifests first. This catches configuration and Helm-template errors
without changing the cluster:

```bash
./platformctl render inventory-app
```

Build and load the image:

```bash
./platformctl build inventory-app --load
```

Deploy it and wait for the readiness probe:

```bash
./platformctl deploy inventory-app --wait
```

Verify the result:

```bash
./platformctl status
curl http://inventory.poc.localhost:8080/healthz
```

## 7. Change application configuration

Edit the corresponding file under `projects/`, then preview and deploy it:

```bash
./platformctl render inventory-app
./platformctl deploy inventory-app --wait
```

For example, changing `replicas: 1` to `replicas: 2` updates the Deployment.
Changing `env`, `port`, `health_path`, `host`, or `image` also changes the pod or
routing configuration during the Helm upgrade.

Use Helm history to inspect revisions:

```bash
helm history inventory-app --namespace poc-inventory-app
```

## 8. Remove an application

Uninstall the Helm release and delete its namespace:

```bash
./platformctl delete inventory-app
```

This does not remove the application folder, Docker image, or
`projects/inventory-app.yaml`. Delete those separately only when they are no
longer needed.

## 9. Troubleshooting

Start with:

```bash
./platformctl status
kubectl get events --namespace poc-feature-flag-admin \
  --sort-by=.lastTimestamp
kubectl describe pod --namespace poc-feature-flag-admin \
  --selector app=feature-flag-admin
kubectl logs deployment/feature-flag-admin \
  --namespace poc-feature-flag-admin
```

### ImagePullBackOff or ErrImagePull

The image is not available inside the kind node, or its tag does not match the
project configuration. Build and load the exact configured image:

```bash
./platformctl build feature-flag-admin --load
```

### Pod remains not ready

Check that the application binds to `0.0.0.0:$PORT` and that its readiness path
returns a successful response. Inspect the pod events and logs for startup
errors.

### Browser URL does not respond

Confirm that the application pod is ready and ingress-nginx is running:

```bash
kubectl get pods --namespace ingress-nginx
kubectl get ingress --all-namespaces
```

If the local cluster does not exist, run `./platformctl bootstrap --target
local` again.

### Application still shows old code

A same-tag image was probably rebuilt while the existing pod continued to run.
Restart the Deployment, or use a new image tag and redeploy.

### Inspect the exact desired resources

Compare the locally rendered output with the installed release:

```bash
./platformctl render feature-flag-admin
helm get manifest feature-flag-admin \
  --namespace poc-feature-flag-admin
```

## 10. Operate against AKS

The intended AKS workflow is:

```bash
RESOURCE_GROUP=poc-platform-rg infra/aks/deploy.sh
./platformctl bootstrap --target aks
./platformctl deploy --wait
```

Before deploying, update `platform.yaml` with the ACR login server, real domain,
and public port. Images must be built and pushed to ACR separately; the current
`build` command builds locally and does not push images.

The AKS Bicep and deployment path have not been exercised against a real Azure
subscription. Treat them as an architectural prototype, not a proven
production runbook.

## 11. Operational limitations

- Data in `/data` is not persistent and is lost when a pod is replaced.
- There is no authentication at the platform boundary.
- There is no TLS, network policy, quota, or centralized observability.
- Project environment variables are not a secrets mechanism.
- Delivery is manual; there is no CI/CD or GitOps reconciliation.

Use this platform to demonstrate the deployment model and application behavior,
not to host production workloads.