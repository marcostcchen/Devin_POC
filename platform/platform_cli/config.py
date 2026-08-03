"""Loading and interpreting the platform's two kinds of configuration.

`platform.yaml` describes the cluster and the mocked directory; each
`projects/<id>.yaml` describes one deployable project. Nothing else is read: a
project's own repository is only ever used to build its image.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parent.parent
PLATFORM_FILE = ROOT / "platform.yaml"
POLICY_FILE = ROOT / "policy.yaml"
PROJECTS_DIR = ROOT / "projects"
CHARTS_DIR = ROOT / "charts"


def _read(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


@dataclass(frozen=True)
class Platform:
    raw: Dict[str, Any]

    @classmethod
    def load(cls, path: Path = PLATFORM_FILE) -> "Platform":
        return cls(_read(path))

    @property
    def _p(self) -> Dict[str, Any]:
        return self.raw.get("platform", {})

    @property
    def name(self) -> str:
        return self._p.get("name", "POC Platform")

    @property
    def domain(self) -> str:
        return self._p["domain"]

    @property
    def namespace_prefix(self) -> str:
        return self._p.get("namespace_prefix", "poc-")

    @property
    def system_namespace(self) -> str:
        return self._p.get("system_namespace", "poc-platform")

    @property
    def registry(self) -> str:
        return (self._p.get("registry") or "").rstrip("/")

    @property
    def ingress_class(self) -> str:
        return self._p.get("ingress_class", "nginx")

    @property
    def tls(self) -> Dict[str, Any]:
        return self._p.get("tls", {}) or {}

    @property
    def public_port(self) -> int | None:
        return self._p.get("public_port")

    @property
    def scheme(self) -> str:
        return "https" if self.tls.get("enabled") else "http"

    @property
    def sizes(self) -> Dict[str, Any]:
        return self.raw.get("sizes", {})

    @property
    def principals(self) -> List[Dict[str, Any]]:
        return self.raw.get("principals", [])

    def namespace(self, project_id: str) -> str:
        return f"{self.namespace_prefix}{project_id}"

    def host(self, subdomain: str) -> str:
        return f"{subdomain}.{self.domain}"

    def url(self, subdomain: str) -> str:
        """The address a browser uses, including the port kind publishes on."""
        port = self.public_port
        default = 443 if self.scheme == "https" else 80
        suffix = "" if port in (None, default) else f":{port}"
        return f"{self.scheme}://{self.host(subdomain)}{suffix}"

    def image(self, repository: str, tag: str) -> str:
        prefix = f"{self.registry}/" if self.registry else ""
        return f"{prefix}{repository}:{tag}"


@dataclass(frozen=True)
class Project:
    path: Path
    raw: Dict[str, Any]

    @classmethod
    def load(cls, path: Path) -> "Project":
        return cls(path, _read(path))

    def section(self, name: str) -> Dict[str, Any]:
        return self.raw.get(name, {}) or {}

    @property
    def id(self) -> str:
        return self.raw.get("id", self.path.stem)

    @property
    def name(self) -> str:
        return self.raw.get("name", self.id)

    @property
    def stage(self) -> str:
        return self.raw.get("stage", "")

    @property
    def subdomain(self) -> str:
        return self.section("route").get("subdomain", self.id)

    @property
    def repo_path(self) -> Path | None:
        """Where the project's own repository is checked out, relative to here.

        Only `platformctl build` uses it: a deployment needs the image, not the
        source.
        """
        repo = self.raw.get("repo")
        if not repo or "://" in repo:
            return None
        return (ROOT / repo).resolve()


def load_projects(directory: Path = PROJECTS_DIR) -> List[Project]:
    """Every project file, in a stable order. `_`-prefixed files are templates."""
    return [
        Project.load(path)
        for path in sorted(directory.glob("*.yaml"))
        if not path.name.startswith("_")
    ]


def load_project(project_id: str, directory: Path = PROJECTS_DIR) -> Project:
    for project in load_projects(directory):
        if project.id == project_id:
            return project
    raise KeyError(f"no project {project_id!r} in {directory}")
