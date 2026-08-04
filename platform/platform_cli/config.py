"""Reading the platform's two kinds of configuration.

`platform.yaml` describes the cluster; each `projects/<id>.yaml` describes one
deployable project. Nothing else is read: a project's own repository is only
ever used to build its image.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parent.parent
PLATFORM_FILE = ROOT / "platform.yaml"
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
    def domain(self) -> str:
        return self.raw["domain"]

    @property
    def registry(self) -> str:
        return (self.raw.get("registry") or "").rstrip("/")

    @property
    def ingress_class(self) -> str:
        return self.raw.get("ingress_class", "nginx")

    def namespace(self, project_id: str) -> str:
        return f"{self.raw.get('namespace_prefix', 'poc-')}{project_id}"

    def url(self, host: str) -> str:
        """The address a browser uses, including the port the ingress is on."""
        port = self.raw.get("public_port", 80)
        suffix = "" if port == 80 else f":{port}"
        return f"http://{host}.{self.domain}{suffix}"


@dataclass(frozen=True)
class Project:
    path: Path
    raw: Dict[str, Any]

    @classmethod
    def load(cls, path: Path) -> "Project":
        return cls(path, _read(path))

    @property
    def id(self) -> str:
        return self.raw.get("id", self.path.stem)

    @property
    def name(self) -> str:
        return self.raw.get("name", self.id)

    @property
    def host(self) -> str:
        return self.raw.get("host", self.id)

    @property
    def image(self) -> str:
        return self.raw["image"]

    @property
    def repo_path(self) -> Path:
        """Where the project's own repository is, relative to this directory."""
        return (ROOT / self.raw["repo"]).resolve()


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
