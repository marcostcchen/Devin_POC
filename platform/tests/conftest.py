import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from platform_cli.config import Platform, Project, load_projects  # noqa: E402
from platform_cli.policy import Policy  # noqa: E402


@pytest.fixture(scope="session")
def platform() -> Platform:
    return Platform.load()


@pytest.fixture(scope="session")
def policy() -> Policy:
    return Policy.load()


@pytest.fixture(scope="session")
def projects() -> list[Project]:
    return load_projects()


@pytest.fixture()
def project_file(tmp_path):
    """Write a project file with the given overrides and load it."""
    import copy

    import yaml

    base = {
        "schema_version": 2,
        "id": "sample",
        "name": "Sample",
        "summary": "A sample project.",
        "owner": "Team",
        "stage": "poc",
        "image": {"repository": "poc/sample", "tag": "0.1.0"},
        "runtime": {"port": 8000, "health_path": "/healthz", "replicas": 1, "size": "small"},
        "route": {"subdomain": "sample"},
        "access": {"roles": ["viewer"], "default_role": "viewer", "group_roles": {}},
        "data": {"classification": "synthetic", "persistence": "ephemeral"},
        "capabilities": ["Something"],
        "limitations": ["Everything else"],
    }

    def make(**overrides) -> Project:
        raw = copy.deepcopy(base)
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(raw.get(key), dict):
                raw[key].update(value)
            else:
                raw[key] = value
        path = tmp_path / f"{raw['id']}.yaml"
        path.write_text(yaml.safe_dump(raw), encoding="utf-8")
        return Project.load(path)

    return make
