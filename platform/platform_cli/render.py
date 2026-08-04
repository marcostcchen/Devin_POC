"""Turning a project file into Helm values.

This is the whole translation layer between "what a team writes" and "what
Kubernetes runs". Every project goes through the same chart, so adding a
project cannot change the shape of what gets deployed.
"""

from __future__ import annotations

from typing import Any, Dict

from platform_cli.config import Platform, Project


def app_values(project: Project, platform: Platform) -> Dict[str, Any]:
    image = project.image
    return {
        "name": project.id,
        "image": f"{platform.registry}/{image}" if platform.registry else image,
        "replicas": project.raw.get("replicas", 1),
        "port": project.raw.get("port", 8000),
        "healthPath": project.raw.get("health_path", "/healthz"),
        "env": {name: str(value) for name, value in (project.raw.get("env") or {}).items()},
        "host": f"{project.host}.{platform.domain}",
        "ingressClassName": platform.ingress_class,
    }
