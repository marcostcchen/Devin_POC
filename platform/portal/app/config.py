"""The portal's view of the platform: one JSON file, mounted from a ConfigMap.

`platformctl` renders it from `platform.yaml`, `policy.yaml` and `projects/*.yaml`,
so the portal never reads the cluster or the repository.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List

CONFIG_PATH = os.environ.get("PORTAL_CONFIG", "/etc/poc-platform/platform.json")


@dataclass(frozen=True)
class Principal:
    email: str
    display_name: str
    groups: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    summary: str
    owner: str
    stage: str
    url: str
    namespace: str
    roles: List[str]
    default_role: str
    group_roles: Dict[str, str]
    capabilities: List[str]
    limitations: List[str]

    def role_for(self, principal: Principal) -> str:
        """The role this project gives a principal, from their directory groups.

        The mapping is walked in declaration order, most privileged first, which
        is the same rule each project applies to the groups the platform
        asserts; resolved here only so the portal can show it on the card.
        """
        held = set(principal.groups)
        for group, role in self.group_roles.items():
            if group in held:
                return role
        return self.default_role


@dataclass(frozen=True)
class PortalConfig:
    name: str
    domain: str
    environment: str
    principals: List[Principal]
    projects: List[Project]
    guardrails: Dict[str, Any]

    def principal(self, email: str) -> Principal | None:
        return next((p for p in self.principals if p.email == email), None)


def load(path: str = CONFIG_PATH) -> PortalConfig:
    with open(path, encoding="utf-8") as handle:
        raw = json.load(handle)
    platform = raw.get("platform", {})
    return PortalConfig(
        name=platform.get("name", "POC Platform"),
        domain=platform.get("domain", ""),
        environment=platform.get("environment", "poc"),
        principals=[Principal(**p) for p in raw.get("principals", [])],
        projects=[Project(**p) for p in raw.get("projects", [])],
        guardrails=raw.get("guardrails", {"allowed": [], "not_allowed": []}),
    )
