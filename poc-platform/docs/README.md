# Documentation

Every page here is also served in the platform console's **Docs** panel.

## The environment

- [poc-environment.md](poc-environment.md) — **what is possible in this POC
  environment and what is not.** Read this before drawing a conclusion from
  anything demonstrated here. The machine-checkable half is enforced from
  [`../policy.yaml`](../policy.yaml).

## Building on the platform

- [platform-contract.md](platform-contract.md) — what an app must do to be
  hosted: the `poc.yaml` manifest, the environment it is started with, health
  checks, identity headers, path prefixes, disposable state.

## Where this is going

- [target-architecture.md](target-architecture.md) — the in-house platform this
  POC is a rehearsal for, and an honest box-by-box mapping of what the POC does
  and does not cover.
- [roadmap.md](roadmap.md) — next-step proposals that close those gaps, each
  with the question it answers.
- [graduating-a-poc.md](graduating-a-poc.md) — the checklist for turning one
  prototype into something a team can depend on.

## Conventions

- One topic per file, kebab-case, first line is an `#` heading — the console
  uses it as the tab title.
- Images live in [`images/`](images/) and are referenced relatively, so they
  render on GitHub and in the console alike.
