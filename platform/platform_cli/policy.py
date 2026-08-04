"""The environment's rules, checked against a project's configuration.

`platformctl validate` runs these, and `deploy` refuses to install a project
that fails one. This is the whole of the platform's governance: the rest of the
platform is routing and identity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

from platform_cli.config import POLICY_FILE, Platform, Project

STORAGE_RE = re.compile(r"^(\d+)Gi$")


@dataclass(frozen=True)
class Policy:
    raw: Dict[str, Any]

    @classmethod
    def load(cls, path: Path = POLICY_FILE) -> "Policy":
        with path.open(encoding="utf-8") as handle:
            return cls(yaml.safe_load(handle) or {})

    @property
    def limits(self) -> Dict[str, Any]:
        return self.raw.get("limits", {})

    @property
    def guardrails(self) -> Dict[str, Any]:
        return {
            "allowed": self.raw.get("allowed", []),
            "not_allowed": self.raw.get("not_allowed", []),
        }

    def violations(self, project: Project, platform: Platform) -> List[str]:
        """Every rule this project breaks, phrased as what to fix."""
        limits = self.limits
        runtime = project.section("runtime")
        access = project.section("access")
        data = project.section("data")
        image = project.section("image")
        problems: List[str] = []

        if project.raw.get("schema_version") != 2:
            problems.append("schema_version must be 2")
        if not re.fullmatch(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?", project.id):
            problems.append(f"id {project.id!r} is not a valid namespace segment")
        if project.path.stem != project.id:
            problems.append(f"file name must match the id ({project.id}.yaml)")
        if project.stage not in limits.get("stages", []):
            problems.append(f"stage {project.stage!r} is not one of {limits.get('stages')}")

        if not image.get("repository"):
            problems.append("image.repository is required")
        tag = str(image.get("tag", ""))
        if not tag:
            problems.append("image.tag is required")
        elif tag in limits.get("forbidden_image_tags", []):
            problems.append(f"image.tag {tag!r} is not pinned")

        if not isinstance(runtime.get("port"), int):
            problems.append("runtime.port must be an integer")
        if not runtime.get("health_path", "").startswith("/"):
            problems.append("runtime.health_path must be an absolute path")
        replicas = runtime.get("replicas", 1)
        if not isinstance(replicas, int) or not 1 <= replicas <= limits.get("max_replicas", 1):
            problems.append(f"runtime.replicas must be 1..{limits.get('max_replicas')}")
        size = runtime.get("size")
        if size not in limits.get("sizes", []):
            problems.append(f"runtime.size {size!r} is not one of {limits.get('sizes')}")
        elif size not in platform.sizes:
            problems.append(f"runtime.size {size!r} has no definition in platform.yaml")

        for name in (runtime.get("env") or {}):
            for pattern in limits.get("forbidden_env_name_patterns", []):
                if re.search(pattern, name):
                    problems.append(
                        f"runtime.env.{name} looks like a credential; this environment has no secret store"
                    )

        roles = access.get("roles") or []
        if not roles:
            problems.append("access.roles must list at least one role")
        if access.get("default_role") not in roles:
            problems.append("access.default_role must be one of access.roles")
        for group, role in (access.get("group_roles") or {}).items():
            if role not in roles:
                problems.append(f"access.group_roles.{group} maps to unknown role {role!r}")

        classification = data.get("classification")
        if classification not in limits.get("data_classifications", []):
            problems.append(
                f"data.classification {classification!r} is not one of "
                f"{limits.get('data_classifications')}"
            )
        persistence = str(data.get("persistence", "ephemeral"))
        if persistence != "ephemeral":
            match = STORAGE_RE.fullmatch(persistence)
            if not match:
                problems.append("data.persistence must be 'ephemeral' or '<n>Gi'")
            elif int(match.group(1)) > limits.get("max_storage_gi", 0):
                problems.append(
                    f"data.persistence {persistence} exceeds the {limits.get('max_storage_gi')}Gi ceiling"
                )

        if len(project.raw.get("limitations") or []) < limits.get("min_limitations", 0):
            problems.append(
                f"at least {limits.get('min_limitations')} limitations must be declared"
            )
        return problems


def cross_violations(projects: Iterable[Project]) -> List[str]:
    """Clashes no single project can see: two of them asking for the same thing."""
    problems: List[str] = []
    for field, values in (
        ("id", [p.id for p in projects]),
        ("route.subdomain", [p.subdomain for p in projects]),
    ):
        seen: Dict[str, int] = {}
        for value in values:
            seen[value] = seen.get(value, 0) + 1
        problems.extend(f"{field} {value!r} is used by {count} projects"
                        for value, count in seen.items() if count > 1)
    return problems
