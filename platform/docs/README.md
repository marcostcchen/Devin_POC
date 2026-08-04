# Documentation

Start with the page written for the question you have.

**"What can I conclude from a demo I just saw?"**
[poc-environment.md](poc-environment.md) — what this environment can and cannot
evidence, and the rules the platform enforces so the answer stays honest.

**"Why does this exist, and what is it worth?"**
[business-view.md](business-view.md) — the platform in business terms: the
problem, the current applications, the value today and the open questions.

**"How does it actually work?"**
[architecture.md](architecture.md) — the pieces, how the local cluster and AKS
stay the same deployment, and how far the isolation between projects goes.

**"I have a prototype. How do I get it on here?"**
[project-contract.md](project-contract.md) — the six environment variables and
one YAML file that is the whole contract.

**"It's deployed and something is wrong."**
[operations.md](operations.md) — the `platformctl` reference, day-2 commands,
the AKS differences, and the failure modes worth knowing in advance.

**"How does this compare to the platform we intend to build?"**
[target-architecture.md](target-architecture.md) — the target mapped box by box
against what is actually here, followed by [roadmap.md](roadmap.md), the
increments that would close each gap.

**"This prototype is working. Now what?"**
[graduating-a-project.md](graduating-a-project.md) — the checklist for making
one real, which is a rewrite of the parts this environment fakes.
