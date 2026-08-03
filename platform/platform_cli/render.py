"""Turning a project file into Helm values, and the catalog the portal reads.

This module is the whole translation layer between "what a team writes" and
"what Kubernetes runs". Every project goes through the same chart, so adding a
project cannot change the shape of what gets deployed.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from platform_cli.config import Platform, Project
from platform_cli.policy import Policy

CPU_RE = re.compile(r"^(\d+(?:\.\d+)?)(m?)$")
MEMORY_RE = re.compile(r"^(\d+)(Mi|Gi)$")


def _cpu_millis(value: str) -> int:
    match = CPU_RE.fullmatch(str(value))
    if not match:
        raise ValueError(f"cannot read cpu quantity {value!r}")
    amount, unit = float(match.group(1)), match.group(2)
    return int(amount if unit == "m" else amount * 1000)


def _memory_mib(value: str) -> int:
    match = MEMORY_RE.fullmatch(str(value))
    if not match:
        raise ValueError(f"cannot read memory quantity {value!r}")
    amount, unit = int(match.group(1)), match.group(2)
    return amount if unit == "Mi" else amount * 1024


def _quota(resources: Dict[str, Any], replicas: int) -> Dict[str, Any]:
    """Room for the running pods plus one, so a rolling update is not blocked."""
    pods = replicas + 1
    return {
        "pods": pods + 2,
        "cpuLimit": f"{_cpu_millis(resources['limits']['cpu']) * pods}m",
        "memoryLimit": f"{_memory_mib(resources['limits']['memory']) * pods}Mi",
        "storageClaims": 2,
    }


def group_roles_value(group_roles: Dict[str, str]) -> str:
    """`group:role,group:role` — the format a project parses from AUTH_GROUP_ROLES."""
    return ",".join(f"{group}:{role}" for group, role in group_roles.items())


def app_values(project: Project, platform: Platform) -> Dict[str, Any]:
    runtime = project.section("runtime")
    access = project.section("access")
    data = project.section("data")
    image = project.section("image")
    resources = platform.sizes[runtime["size"]]
    persistence = str(data.get("persistence", "ephemeral"))
    tls = platform.tls

    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "summary": project.raw.get("summary", ""),
            "owner": project.raw.get("owner", ""),
            "stage": project.stage,
        },
        "namespace": platform.namespace(project.id),
        "image": {
            "repository": (
                f"{platform.registry}/{image['repository']}"
                if platform.registry
                else image["repository"]
            ),
            "tag": str(image["tag"]),
            "pullPolicy": image.get("pull_policy", "IfNotPresent"),
        },
        "runtime": {
            "port": runtime["port"],
            "healthPath": runtime["health_path"],
            "replicas": runtime.get("replicas", 1),
            "resources": resources,
            "env": {name: str(value) for name, value in (runtime.get("env") or {}).items()},
        },
        "route": {
            "host": platform.host(project.subdomain),
            "ingressClassName": platform.ingress_class,
            "tls": {
                "enabled": bool(tls.get("enabled")),
                "clusterIssuer": tls.get("cluster_issuer", ""),
            },
        },
        "access": {
            "defaultRole": access["default_role"],
            "groupRoles": group_roles_value(access.get("group_roles") or {}),
            "roles": ",".join(access.get("roles") or []),
        },
        "auth": {
            "url": f"http://poc-portal.{platform.system_namespace}.svc.cluster.local/auth",
            "signinUrl": f"{platform.url('portal')}/login",
            "responseHeaders": "X-Auth-Request-Email,X-Auth-Request-User,X-Auth-Request-Groups",
        },
        "data": {
            "classification": data.get("classification", "synthetic"),
            "persistence": {
                "enabled": persistence != "ephemeral",
                "size": "1Gi" if persistence == "ephemeral" else persistence,
                "storageClass": data.get("storage_class", ""),
            },
        },
        "quota": _quota(resources, runtime.get("replicas", 1)),
    }


def portal_catalog(platform: Platform, projects: List[Project], policy: Policy) -> Dict[str, Any]:
    """The JSON the portal serves its catalog and its mocked directory from."""
    return {
        "platform": {
            "name": platform.name,
            "domain": platform.domain,
            "environment": policy.raw.get("environment", "poc"),
        },
        "principals": [
            {
                "email": principal["email"],
                "display_name": principal.get("display_name", principal["email"]),
                "groups": list(principal.get("groups") or []),
            }
            for principal in platform.principals
        ],
        "projects": [
            {
                "id": project.id,
                "name": project.name,
                "summary": project.raw.get("summary", ""),
                "owner": project.raw.get("owner", ""),
                "stage": project.stage,
                "url": platform.url(project.subdomain),
                "namespace": platform.namespace(project.id),
                "roles": list(project.section("access").get("roles") or []),
                "default_role": project.section("access").get("default_role", ""),
                "group_roles": dict(project.section("access").get("group_roles") or {}),
                "capabilities": list(project.raw.get("capabilities") or []),
                "limitations": list(project.raw.get("limitations") or []),
            }
            for project in projects
        ],
        "guardrails": policy.guardrails,
    }


def portal_values(
    platform: Platform, projects: List[Project], policy: Policy, tag: str = "0.1.0"
) -> Dict[str, Any]:
    tls = platform.tls
    return {
        "namespace": platform.system_namespace,
        "image": {
            "repository": (
                f"{platform.registry}/poc/poc-portal" if platform.registry else "poc/poc-portal"
            ),
            "tag": tag,
            "pullPolicy": "IfNotPresent",
        },
        "route": {
            "host": platform.host("portal"),
            "ingressClassName": platform.ingress_class,
            "tls": {
                "enabled": bool(tls.get("enabled")),
                "clusterIssuer": tls.get("cluster_issuer", ""),
            },
        },
        "cookieDomain": platform.domain,
        "config": portal_catalog(platform, projects, policy),
    }
