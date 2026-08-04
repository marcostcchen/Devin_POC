"""What a project file turns into: Helm values, and the manifests behind them."""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

from platform_cli.config import CHARTS_DIR, load_project, load_projects
from platform_cli.render import app_values

pytestmark = pytest.mark.usefixtures("platform")


def test_a_project_gets_its_own_hostname(platform):
    values = app_values(load_project("kyc-review-queue"), platform)
    assert values["host"] == "kyc.poc.localhost"
    assert platform.namespace("kyc-review-queue") == "poc-kyc-review-queue"


def test_the_defaults_cover_what_a_project_file_leaves_out(platform):
    values = app_values(load_project("kyc-review-queue"), platform)
    assert (values["port"], values["healthPath"], values["replicas"]) == (8000, "/healthz", 1)


def test_extra_configuration_reaches_the_container(platform):
    values = app_values(load_project("refunds-dashboard"), platform)
    assert values["env"]["APPROVAL_THRESHOLD_AMOUNT"] == "200"


def test_every_project_has_its_own_hostname_and_namespace(platform):
    projects = load_projects()
    hosts = [app_values(project, platform)["host"] for project in projects]
    assert len(set(hosts)) == len(projects)


def _template(chart: Path, values: dict, namespace: str) -> list[dict]:
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
def test_the_chart_renders_the_three_objects_a_project_needs(platform):
    project = load_project("kyc-review-queue")
    docs = _template(
        CHARTS_DIR / "poc-app", app_values(project, platform), platform.namespace(project.id)
    )
    assert {doc["kind"] for doc in docs} == {"Deployment", "Service", "Ingress"}


@needs_helm
def test_the_container_gets_the_runtime_contract(platform):
    project = load_project("refunds-dashboard")
    docs = _template(
        CHARTS_DIR / "poc-app", app_values(project, platform), platform.namespace(project.id)
    )
    container = next(
        doc for doc in docs if doc["kind"] == "Deployment"
    )["spec"]["template"]["spec"]["containers"][0]
    env = {item["name"]: item["value"] for item in container["env"]}
    assert env["PORT"] == "8000"
    assert env["DATA_DIR"] == "/data"
    assert env["APPROVAL_THRESHOLD_AMOUNT"] == "200"
    assert container["readinessProbe"]["httpGet"]["path"] == "/healthz"


@needs_helm
def test_the_ingress_publishes_the_project_hostname(platform):
    project = load_project("kyc-review-queue")
    docs = _template(
        CHARTS_DIR / "poc-app", app_values(project, platform), platform.namespace(project.id)
    )
    ingress = next(doc for doc in docs if doc["kind"] == "Ingress")
    assert ingress["spec"]["rules"][0]["host"] == "kyc.poc.localhost"
    assert ingress["spec"]["ingressClassName"] == "nginx"
