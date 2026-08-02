# The platform contract

Everything a prototype must do to be hosted, in one page. The three prototypes
in this repository are the reference implementations.

## 1. Ship a `poc.yaml`

At the root of the prototype's folder. The platform scans one level below the
repository root for this file, so adding an app is a file, not a code change.

```yaml
schema_version: 1
id: my-poc                      # lowercase, also the URL segment
name: My POC
summary: One sentence for the console card.
owner: Team or squad
stage: poc                      # poc | prototype
stack: [FastAPI, SQLite]

runtime:
  command: ./run.sh             # started from the app directory, must honour $PORT
  port: 8002                    # unique across the repository
  health_path: /healthz
  ready_timeout_seconds: 300    # cold start includes dependency installation

identity:
  mode: platform-headers
  roles: [analyst, senior_reviewer]
  default_role: analyst         # least privilege

data:
  classification: synthetic     # synthetic | anonymized-sample
  store: sqlite                 # sqlite | memory | file
  reset_command: rm -f "$PLATFORM_DATA_DIR/my.db"

capabilities: [What it genuinely demonstrates]
limitations: [What it fakes or leaves out]
docs: [README.md]
```

The registry validates this on load and refuses to start anything that breaks
[environment policy](poc-environment.md#rules-the-platform-enforces-for-you).

## 2. Accept the environment

The supervisor starts `runtime.command` from the app directory with:

| Variable | Meaning |
| --- | --- |
| `PORT` | Port to listen on. Same value as `runtime.port` |
| `PLATFORM_MANAGED` | `1` when supervised by the platform; unset standalone |
| `PLATFORM_APP_ID` | The manifest `id` |
| `PLATFORM_BASE_PATH` | Mount point, e.g. `/apps/my-poc` |
| `PLATFORM_DATA_DIR` | Writable directory for databases; wiped by `reset.sh` |
| `PLATFORM_GATEWAY_URL` | Gateway origin, for app-to-app calls |

Every prototype must still run standalone with none of these set. All three here
do: `PLATFORM_DATA_DIR` falls back to the app folder, `PLATFORM_BASE_PATH` to
`""`, and the local identity switcher comes back.

## 3. Answer a health check

`GET {health_path}` returning any 2xx/3xx before `ready_timeout_seconds`. The
gateway serves a "not running" page instead of a connection error until it does.

## 4. Trust the platform's identity headers

Injected on every proxied request, and stripped from the incoming request first
so a browser cannot spoof them:

| Header | Meaning |
| --- | --- |
| `X-Platform-User` | Persona email |
| `X-Platform-User-Name` | Display name |
| `X-Platform-Role` | Role **for this app**, mapped from `platform.yaml` |
| `X-Platform-Platform-Role` | Platform-level role (`platform_admin`, `reviewer`, `observer`) |
| `X-Platform-Base-Path` | Mount point |
| `X-Platform-Request-Id` | Correlation id |

Rules:

- Only honour them when `PLATFORM_MANAGED=1`; otherwise fall back to the app's
  own mocked identity so standalone runs are unchanged.
- Reject a role the app does not implement rather than guessing.
- Report the identity through the app's own `me` endpoint with a
  `platform_managed` flag, and hide the app's local persona switcher when it is
  set - the console owns that choice.

The gateway maps personas to app roles in `platform.yaml`; a role that is not in
the manifest's `identity.roles` degrades to `default_role`, and the console
lists the mismatch as a configuration problem.

## 5. Work under a path prefix

The gateway forwards `/apps/<id>/<path>` to `http://127.0.0.1:<port>/apps/<id>/<path>`
— the prefix is **kept**, and the app is told about it through
`PLATFORM_BASE_PATH`. Stripping it instead would leave every framework
generating URLs one level up from where the browser is:

- FastAPI: `FastAPI(root_path=PLATFORM_BASE_PATH)`. Routes and `StaticFiles`
  mounts then resolve under the prefix, and `/docs` keeps working.
- Express: mount the whole app once, `app.use(basePath || "/", router)`.
- Health checks are the exception: the supervisor probes `health_path` on the
  app's own port with no prefix, so keep that route reachable both ways
  (FastAPI does this for free; in Express register it outside the mount).
- Frontends: for Vite set `base` from `PLATFORM_BASE_PATH` and derive the API
  root from `import.meta.env.BASE_URL`; for plain HTML use relative
  `src`/`fetch` paths, which resolve against the mount point.
- A request to `/apps/<id>` (no trailing slash) is redirected to `/apps/<id>/`
  so those relative URLs resolve correctly.
- Upstream `Location` headers that are not already prefixed are rewritten into
  the mount point.

## 6. Keep state disposable

Write databases and files under `PLATFORM_DATA_DIR`, seed on first start, and
make `reset_command` restore a fresh dataset.

## Registering a new prototype

1. `mkdir my-poc`, add the app and a `run.sh` that honours `$PORT`.
2. Add `poc.yaml`.
3. Give each persona in `poc-platform/platform.yaml` a role for the new app.
4. Open the console and press **Rescan manifests**, then **Start**.

## What the platform deliberately does not do

- No build, deploy or container: `run.sh` runs on your machine as you.
- No authentication of its own console; anyone who can reach it is an admin.
- No request streaming (responses are buffered), no WebSocket proxying.
- No restart-on-crash, no log rotation, no resource limits.
- No versioning of the contract beyond `schema_version`.
