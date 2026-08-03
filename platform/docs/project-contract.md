# The project contract

Everything a repository must do to be deployable by the platform. It is short on
purpose: a project depends on its own stack, never on this one.

## The runtime side (in your repository)

1. **Ship a Dockerfile.** Any base image, any language. It must run as a
   non-root user (uid `10001` is what the chart runs it as) with a read-only
   root filesystem.
2. **Listen on `$PORT`**, on `0.0.0.0`.
3. **Answer the health path** (`/healthz` by convention) with `200` once the
   process is ready to serve. It is used as startup, readiness and liveness
   probe.
4. **Write only to `$DATA_DIR`** (`/data`), and to `/tmp`. Everything else is
   read-only. Assume the directory is empty on every start unless the project
   asked for persistence.
5. **Accept the identity the platform asserts.** When `AUTH_MODE=proxy-headers`:

   | Header | Meaning |
   | --- | --- |
   | `X-Auth-Request-Email` | The caller. Absent means unauthenticated — return 401 |
   | `X-Auth-Request-User` | Display name |
   | `X-Auth-Request-Groups` | Comma-separated directory groups |

   Map groups to your own roles with `AUTH_GROUP_ROLES`
   (`group:role,group:role`, most privileged first: the first group the caller
   holds decides) and fall back to `AUTH_DEFAULT_ROLE`. Enforce the role
   server-side; the platform authenticates, it does not authorize.
6. **Still run standalone.** Without `AUTH_MODE` the project is on its own: use
   a local roster, a dev login, whatever suits — `./run.sh` must still work in a
   checkout with no cluster anywhere.

That is the whole runtime contract — six environment variables, all of them
optional in the sense that the app must have a sane default for each:

```
PORT=8000  DATA_DIR=/data  AUTH_MODE=proxy-headers
AUTH_DEFAULT_ROLE=analyst  AUTH_GROUP_ROLES=kyc-seniors:senior_reviewer,kyc-analysts:analyst
```

Nothing named `PLATFORM_*` exists, there is no base path to honour (each project
owns a hostname, not a path prefix), and no SDK to import.

## The platform side (one file here)

`projects/<id>.yaml`, copied from [`_template.yaml`](../projects/_template.yaml):

```yaml
schema_version: 2
id: kyc-review-queue                 # namespace poc-kyc-review-queue, and the release name
name: KYC Review Queue
summary: One sentence, shown on the portal card.
owner: Compliance Ops
stage: poc                           # poc | prototype
repo: ../kyc-review-queue            # optional, only `platformctl build` uses it

image:
  repository: poc/kyc-review-queue   # prefixed with platform.registry when set
  tag: "0.1.0"                       # pinned; latest/main/master are rejected

runtime:
  port: 8000
  health_path: /healthz
  replicas: 1
  size: small                        # small | medium, from platform.yaml
  env: {}                            # plain config only; credential-shaped names are rejected

route:
  subdomain: kyc                     # https://kyc.<platform domain>

access:
  roles: [analyst, senior_reviewer]  # the roles the project implements
  default_role: analyst              # least privilege for an unmapped caller
  group_roles:                       # directory group -> project role
    kyc-seniors: senior_reviewer
    kyc-analysts: analyst

data:
  classification: synthetic          # synthetic | anonymized-sample
  persistence: ephemeral             # ephemeral | <n>Gi

capabilities: [What it genuinely demonstrates]
limitations: [What it fakes or leaves out]
```

`capabilities` and `limitations` are not decoration: the portal renders them on
the project's card, so a reviewer sees what a demo can and cannot answer before
clicking into it. A project with no `limitations` fails validation.

## What the platform does with it

```
./platformctl validate            # policy.yaml, before anything is created
./platformctl render <id>         # the manifests, without applying them
./platformctl deploy <id>         # helm upgrade --install, one generic chart
```

Out of that one file the chart creates: the namespace (Pod Security Admission
`restricted`), a resource quota and limit range sized from `size` × `replicas`,
a service account with no API token, default-deny ingress and egress
NetworkPolicies plus an allow rule for the ingress controller and DNS, the
deployment (non-root, read-only root filesystem, all capabilities dropped, three
probes), a service, optionally a PVC, and the ingress with the authentication
subrequest.

## Graduating

When a prototype outgrows the environment, the runtime contract is the part that
survives: a container that listens on a port, reads its identity from headers
and writes to one directory is already deployable next to real services. What
has to be rebuilt is what the platform fakes — see
[graduating-a-project.md](graduating-a-project.md).
