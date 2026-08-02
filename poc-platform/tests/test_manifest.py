"""Manifest schema, and the manifests actually shipped in this repository."""

import pytest

from platform_core.manifest import Manifest, ManifestError, load_manifest

EXPECTED_APPS = {"feature-flag-admin", "kyc-review-queue", "refunds-dashboard"}


def test_every_prototype_ships_a_valid_manifest(repo_manifests):
    assert EXPECTED_APPS <= set(repo_manifests)


def test_manifest_ports_do_not_collide(repo_manifests):
    ports = [manifest.runtime.port for manifest in repo_manifests.values()]
    assert len(ports) == len(set(ports))


def test_base_path_is_derived_from_the_id(manifest):
    assert manifest.base_path == "/apps/example-poc"


def test_default_role_must_be_one_of_the_declared_roles(manifest_data):
    manifest_data["identity"]["default_role"] = "superuser"
    with pytest.raises(ValueError, match="default_role"):
        Manifest.model_validate(manifest_data)


def test_health_path_must_be_absolute(manifest_data):
    manifest_data["runtime"]["health_path"] = "healthz"
    with pytest.raises(ValueError, match="health_path"):
        Manifest.model_validate(manifest_data)


def test_capabilities_and_limitations_are_required(manifest_data):
    manifest_data["limitations"] = []
    with pytest.raises(ValueError):
        Manifest.model_validate(manifest_data)


def test_missing_file_is_reported_as_a_manifest_error(tmp_path):
    with pytest.raises(ManifestError, match="no manifest"):
        load_manifest(str(tmp_path / "poc.yaml"))


def test_invalid_yaml_is_reported_as_a_manifest_error(tmp_path):
    path = tmp_path / "poc.yaml"
    path.write_text("id: [unclosed\n", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(str(path))
