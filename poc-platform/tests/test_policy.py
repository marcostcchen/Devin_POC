"""What this environment refuses to host."""

from platform_core.manifest import Manifest


def test_shipped_prototypes_comply(policy, repo_manifests):
    for app_id, manifest in repo_manifests.items():
        assert policy.check_manifest(manifest) == [], app_id


def test_real_data_is_rejected(policy, manifest_data):
    manifest_data["data"]["classification"] = "production-export"
    violations = policy.check_manifest(Manifest.model_validate(manifest_data))
    assert any("real data may not be used here" in violation for violation in violations)


def test_shared_database_is_rejected(policy, manifest_data):
    manifest_data["data"]["store"] = "postgres"
    violations = policy.check_manifest(Manifest.model_validate(manifest_data))
    assert any("local and disposable" in violation for violation in violations)


def test_production_stage_is_rejected(policy, manifest_data):
    manifest_data["stage"] = "production"
    violations = policy.check_manifest(Manifest.model_validate(manifest_data))
    assert any("only hosts prototypes" in violation for violation in violations)


def test_guardrails_are_documented_for_the_console(policy):
    assert policy.allowed and policy.not_allowed
    assert all(rule.instead for rule in policy.not_allowed)
