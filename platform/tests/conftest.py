import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from platform_cli.config import Platform, Project, load_projects  # noqa: E402


@pytest.fixture(scope="session")
def platform() -> Platform:
    return Platform.load()


@pytest.fixture(scope="session")
def projects() -> list[Project]:
    return load_projects()
