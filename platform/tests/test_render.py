"""What a project file turns into: Helm values, and the manifests behind them."""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

from platform_cli.config import CHARTS_DIR, load_project
from platform_cli.render import app_values, portal_catalog, portal_values

pytestmark = pytest.mark.usefixtures("platform")


def test_values_place_the_project_in_its_own_namespace(platform):
    values = app_values(load_project("kyc-review-queue"), platform)
    assert values["namespace"] == "poc-kyc-review-queue"
    assert values["route"]["host"] == "kyc.poc.localhost"


def test_group_roles_are_flattened_in_precedence_order(platform):
    values = app_values(load_project("kyc-review-queue"), platform)
    assert values["access"]["groupRoles"] == "kyc-seniors:senior_reviewer,kyc-analysts:analyst"
    assert values["access"]["defaultRole"] == "analyst"


def test_the_quota_leaves_room_for_one_extra_pod(platform):
    values = app_values(load_project("kyc-review-queue"), platform)
    # one replica of a "small" project: 2 x 500m CPU and 2 x 512Mi.
    assert values["quota"]["cpuLimit"] == "1000m"
    assert values["quota"]["memoryLimit"] == "1024Mi"


def test_ephemeral_data_asks_for_no_volume(platform):
    values = app_values(load_project("feature-flag-admin"), platform)
    assert values["data"]["persistence"]["enabled"] is False


def test_the_catalog_resolves_a_role_per_project(platform, projects, policy):
    catalog = portal_catalog(platform, projects, policy)
    kyc = next(p for p in catalog["projects"] if p["id"] == "kyc-review-queue")
    assert kyc["group_roles"]["kyc-seniors"] == "senior_reviewer"
    assert kyc["url"] == "http://kyc.poc.localhost:8080"
    assert catalog["guardrails"]["not_allowed"], "the portal shows the environment's limits"


def _template(chart: Path, values: dict, namespace: str = "poc-platform") -> list[dict]:
    """Render a chart the way platformctl does: every release lives in the
    platform namespace, and the manifests place themselves elsewhere."""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml") as handle:
        yaml.safe_dump(values, handle)
        handle.flush()
        output = subprocess.run(
            ["helm", "template", "release", str(chart), "--namespace", namespace,
             "--values", handle.name],
            capture_output=True, text=True, check=True,
        ).stdout
    return [doc for doc in yaml.safe_load_all(output) if doc]


needs_helm = pytest.mark.skipif(shutil.which("helm") is None, reason="helm is not installed")


@needs_helm
def test_the_chart_renders_an_isolated_namespace(platform):
    project = load_project("kyc-review-queue")
    values = app_values(project, platform)
    docs = _template(CHARTS_DIR / "poc-app", values)
    kinds = {doc["kind"] for doc in docs}
    assert {"Namespace", "ResourceQuota", "NetworkPolicy", "Deployment", "Service", "Ingress"} <= kinds
    assert all(
        doc["metadata"].get("namespace", values["namespace"]) == values["namespace"]
        for doc in docs
    )

    namespace = next(doc for doc in docs if doc["kind"] == "Namespace")
    assert namespace["metadata"]["labels"]["pod-security.kubernetes.io/enforce"] == "restricted"

    policies = [doc for doc in docs if doc["kind"] == "NetworkPolicy"]
    deny = next(p for p in policies if p["metadata"]["name"].endswith("default-deny"))
    assert deny["spec"]["podSelector"] == {} and set(deny["spec"]["policyTypes"]) == {
        "Ingress",
        "Egress",
    }


@needs_helm
def test_every_request_goes_through_the_auth_subrequest(platform):
    project = load_project("kyc-review-queue")
    values = app_values(project, platform)
    docs = _template(CHARTS_DIR / "poc-app", values)
    ingress = next(doc for doc in docs if doc["kind"] == "Ingress")
    annotations = ingress["metadata"]["annotations"]
    assert annotations["nginx.ingress.kubernetes.io/auth-url"].endswith("/auth")
    assert "X-Auth-Request-Email" in annotations["nginx.ingress.kubernetes.io/auth-response-headers"]


@needs_helm
def test_the_container_gets_the_runtime_contract_and_nothing_else(platform):
    project = load_project("kyc-review-queue")
    values = app_values(project, platform)
    docs = _template(CHARTS_DIR / "poc-app", values)
    container = next(
        doc for doc in docs if doc["kind"] == "Deployment"
    )["spec"]["template"]["spec"]["containers"][0]
    env = {item["name"]: item["value"] for item in container["env"]}
    assert env["PORT"] == "8000"
    assert env["DATA_DIR"] == "/data"
    assert env["AUTH_MODE"] == "proxy-headers"
    assert env["AUTH_GROUP_ROLES"] == "kyc-seniors:senior_reviewer,kyc-analysts:analyst"
    assert container["securityContext"]["readOnlyRootFilesystem"] is True


@needs_helm
def test_the_portal_chart_carries_the_catalog(platform, projects, policy):
    values = portal_values(platform, projects, policy)
    docs = _template(CHARTS_DIR / "poc-portal", values)
    config_map = next(doc for doc in docs if doc["kind"] == "ConfigMap")
    catalog = json.loads(config_map["data"]["platform.json"])
    assert [p["id"] for p in catalog["projects"]] == [p.id for p in projects]
