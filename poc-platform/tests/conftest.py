"""Fixtures: the real repository manifests, plus a synthetic one to mutate."""

import os

import pytest

from platform_core.config import PLATFORM_DIR, default_config_path, load_config
from platform_core.manifest import Manifest
from platform_core.policy import default_policy_path, load_policy
from platform_core.registry import discover_manifests

REPO_ROOT = os.path.dirname(PLATFORM_DIR)

VALID_MANIFEST = {
    "schema_version": 1,
    "id": "example-poc",
    "name": "Example POC",
    "summary": "A prototype used by the platform tests.",
    "owner": "Platform Experiments",
    "stage": "poc",
    "stack": ["FastAPI"],
    "runtime": {"command": "./run.sh", "port": 9100},
    "identity": {"mode": "platform-headers", "roles": ["admin", "viewer"], "default_role": "viewer"},
    "data": {"classification": "synthetic", "store": "sqlite"},
    "capabilities": ["Does the thing"],
    "limitations": ["Fakes the other thing"],
}


@pytest.fixture()
def manifest_data() -> dict:
    return {key: dict(value) if isinstance(value, dict) else value for key, value in VALID_MANIFEST.items()}


@pytest.fixture()
def manifest(manifest_data: dict) -> Manifest:
    return Manifest.model_validate(manifest_data)


@pytest.fixture(scope="session")
def policy():
    return load_policy(default_policy_path(PLATFORM_DIR))


@pytest.fixture(scope="session")
def platform_config():
    return load_config(default_config_path(PLATFORM_DIR))


@pytest.fixture(scope="session")
def repo_manifests() -> dict[str, Manifest]:
    found, errors = discover_manifests(REPO_ROOT)
    assert not errors, f"unloadable manifests: {errors}"
    return {app_id: manifest for app_id, (manifest, _) in found.items()}
