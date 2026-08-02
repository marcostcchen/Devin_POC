# POC Platform

The shell the prototypes in this repository run on: one console, one URL, one
identity, and one place that states what this environment can and cannot do.

```bash
cd poc-platform
./run.sh            # venv + pip install, gateway on :8080
```

Open <http://localhost:8080> and press **Start** on a card. The first start of an
app installs its dependencies and builds its frontend, so it takes a few minutes;
the card shows `starting…` until its health check passes, and **Logs** streams
the output.

## What it gives you

| | |
| --- | --- |
| **Console** | Every prototype as a card: status, port, your role there, what it demonstrates, what it fakes |
| **Supervisor** | Start / stop / restart each prototype, with health checks and log tails |
| **Gateway** | `/apps/<id>/` reverse-proxies to the app, so everything shares one origin |
| **Mocked SSO** | Pick a persona once; every prototype receives it, mapped to the role *that* app understands |
| **Policy** | Manifests are validated against `policy.yaml`; a prototype that breaks a rule cannot be started |
| **Docs** | [What is possible here and what is not](docs/poc-environment.md), rendered in the console |

## Docs

[`docs/`](docs/) is the documentation folder; every page is also a tab in the
console.

- [POC environment: possible vs not possible](docs/poc-environment.md) — read this first.
- [The platform contract](docs/platform-contract.md) — what an app must do to be hosted.
- [Target architecture](docs/target-architecture.md) — the platform this POC rehearses,
  and what it does and does not cover.
- [Next-step proposals](docs/roadmap.md) — the increments that close those gaps.
- [Graduating a prototype](docs/graduating-a-poc.md) — the checklist for making one real.

## Layout

```
poc-platform/
  platform.yaml       gateway settings and the shared personas
  policy.yaml         the rules of this environment (enforced + documented)
  run.sh              start the gateway
  reset.sh            delete every prototype's database and logs
  platform_core/
    manifest.py       poc.yaml schema and loader
    policy.py         environment policy + per-manifest violations
    config.py         platform.yaml, personas, state directories
    identity.py       persona -> per-app role, and the injected headers
    registry.py       manifest discovery, compliance, app lifecycle
    supervisor.py     child processes, env contract, health, logs
    proxy.py          /apps/<id>/... -> 127.0.0.1:<port>/...
    main.py           FastAPI: console, platform API, proxy routes
  console/            the console UI (plain HTML/CSS/JS, no build step)
  docs/               environment, contract, target architecture, roadmap, graduation
    images/           diagrams referenced by the docs
  tests/              manifest, policy, identity and gateway tests
  .data/              runtime state: per-app databases and logs (gitignored)
```

## Configuration

`platform.yaml` holds the gateway port, the personas and their per-app roles.
Nothing else is configurable, on purpose.

```yaml
gateway:
  port: 8080
  autostart: none        # "all", or a list of app ids
principals:
  - email: ada@example.com
    display_name: Ada Lovelace
    app_roles:
      feature-flag-admin: admin
      kyc-review-queue: senior_reviewer
      refunds-dashboard: finance_approver
```

A persona mapped to a role a prototype does not declare is reported in the
console as a configuration problem, and that prototype falls back to its least
privileged role.

## Tests

```bash
./.venv/bin/python -m pytest tests -q
```

They cover the manifest schema, the policy checks (real data, shared databases
and production stages are rejected), persona-to-role mapping, and the gateway:
prefix stripping, identity injection, spoofed-header stripping and redirect
rewriting against a stub prototype.

## Running a prototype without the platform

Every app still works on its own — `cd feature-flag-admin && ./run.sh` — with its
own identity switcher and its database back in its own folder. The platform is
additive; nothing depends on it being there.
