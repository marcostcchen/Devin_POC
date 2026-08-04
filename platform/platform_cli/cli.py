"""`platformctl` — deploy a project onto the platform, or take it away again.

Every command is a thin wrapper over helm/kubectl/docker: there is no state
here and nothing running in the background. The unit of work is a project file,
and the unit of isolation is its namespace.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Sequence

import yaml

from platform_cli.config import (
    CHARTS_DIR,
    PROJECTS_DIR,
    Platform,
    Project,
    load_project,
    load_projects,
)
from platform_cli.render import app_values

APP_CHART = CHARTS_DIR / "poc-app"
BOOTSTRAP_DIR = CHARTS_DIR.parent / "bootstrap"
KIND_CONFIG = CHARTS_DIR.parent / "local" / "kind-cluster.yaml"


class Failure(Exception):
    """Something the user has to fix; printed without a traceback."""


def run(command: Sequence[str], capture: bool = False, check: bool = True) -> str:
    printable = " ".join(command)
    if not capture:
        print(f"$ {printable}", file=sys.stderr)
    result = subprocess.run(command, capture_output=capture, text=True)
    if check and result.returncode != 0:
        raise Failure(f"command failed: {printable}\n{result.stderr or ''}".rstrip())
    return result.stdout if capture else ""


def _values_file(values: Dict[str, Any], stack: List[str]) -> str:
    handle = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
    yaml.safe_dump(values, handle, sort_keys=False)
    handle.close()
    stack.append(handle.name)
    return handle.name


def _selected(ids: Sequence[str]) -> List[Project]:
    return [load_project(project_id) for project_id in ids] if ids else load_projects()


# --- commands ---------------------------------------------------------------


def cmd_list(args: argparse.Namespace, platform: Platform) -> int:
    for project in load_projects():
        print(
            f"{project.id:<22} {platform.namespace(project.id):<26} "
            f"{platform.url(project.host)}"
        )
    return 0


def cmd_render(args: argparse.Namespace, platform: Platform) -> int:
    project = load_project(args.project)
    temp: List[str] = []
    try:
        print(
            run(
                [
                    "helm", "template", project.id, str(APP_CHART),
                    "--namespace", platform.namespace(project.id),
                    "--values", _values_file(app_values(project, platform), temp),
                ],
                capture=True,
            )
        )
    finally:
        for path in temp:
            Path(path).unlink(missing_ok=True)
    return 0


def cmd_deploy(args: argparse.Namespace, platform: Platform) -> int:
    projects = _selected(args.project)
    temp: List[str] = []
    try:
        for project in projects:
            command = [
                "helm", "upgrade", "--install", project.id, str(APP_CHART),
                "--namespace", platform.namespace(project.id), "--create-namespace",
                "--values", _values_file(app_values(project, platform), temp),
            ]
            if args.wait:
                command += ["--wait", "--timeout", args.timeout]
            run(command)
    finally:
        for path in temp:
            Path(path).unlink(missing_ok=True)
    print("\ndeployed:")
    for project in projects:
        print(f"  {project.name}: {platform.url(project.host)}")
    return 0


def cmd_delete(args: argparse.Namespace, platform: Platform) -> int:
    for project_id in args.project:
        namespace = platform.namespace(project_id)
        run(["helm", "uninstall", project_id, "--namespace", namespace])
        run(["kubectl", "delete", "namespace", namespace, "--ignore-not-found"])
    return 0


def cmd_status(args: argparse.Namespace, platform: Platform) -> int:
    for project in load_projects():
        pods = run(
            [
                "kubectl", "get", "pods",
                "--namespace", platform.namespace(project.id), "-o", "json",
            ],
            capture=True,
            check=False,
        )
        items = json.loads(pods or "{}").get("items", [])
        states = [
            f"{pod['metadata']['name']} {pod['status'].get('phase', '?')}"
            + ("" if _ready(pod) else " (not ready)")
            for pod in items
        ] or ["not deployed"]
        print(f"{project.id:<22} {platform.url(project.host):<40} {'; '.join(states)}")
    return 0


def _ready(pod: Dict[str, Any]) -> bool:
    return all(
        status.get("ready") for status in pod.get("status", {}).get("containerStatuses", [])
    )


def cmd_build(args: argparse.Namespace, platform: Platform) -> int:
    for project in _selected(args.project):
        context = project.repo_path
        if not context.exists():
            raise Failure(f"{project.id}: repo {project.raw['repo']!r} is not a local path")
        run(["docker", "build", "-t", project.image, str(context)])
        if args.load:
            run(["kind", "load", "docker-image", project.image, "--name", args.kind_cluster])
    return 0


def cmd_bootstrap(args: argparse.Namespace, platform: Platform) -> int:
    """Everything the cluster needs before the first project: an ingress."""
    if args.target == "local":
        clusters = run(["kind", "get", "clusters"], capture=True, check=False).split()
        if args.kind_cluster not in clusters:
            run(["kind", "create", "cluster", "--name", args.kind_cluster,
                 "--config", str(KIND_CONFIG)])
    run(["helm", "repo", "add", "ingress-nginx", "https://kubernetes.github.io/ingress-nginx"])
    run(["helm", "repo", "update", "ingress-nginx"])
    run(
        [
            "helm", "upgrade", "--install", "ingress-nginx", "ingress-nginx/ingress-nginx",
            "--version", args.ingress_version,
            "--namespace", "ingress-nginx", "--create-namespace",
            "--values", str(BOOTSTRAP_DIR / f"ingress-nginx.{args.target}.yaml"),
            "--wait", "--timeout", "5m",
        ]
    )
    print("\nthe cluster is ready; now: ./platformctl build --load && ./platformctl deploy")
    return 0


def cmd_new(args: argparse.Namespace, platform: Platform) -> int:
    destination = PROJECTS_DIR / f"{args.id}.yaml"
    if destination.exists():
        raise Failure(f"{destination} already exists")
    text = (PROJECTS_DIR / "_template.yaml").read_text(encoding="utf-8")
    # The template's header addresses whoever is copying it by hand; a
    # scaffolded file starts at the configuration instead.
    body = text[text.index("id:"):]
    destination.write_text(body.replace("my-project", args.id), encoding="utf-8")
    print(f"created {destination}\nedit it, then: ./platformctl deploy {args.id}")
    return 0


# --- entrypoint -------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="platformctl", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="every project, its namespace and its URL")

    render = sub.add_parser("render", help="print the Kubernetes manifests for a project")
    render.add_argument("project")

    deploy = sub.add_parser("deploy", help="install or upgrade projects (all of them by default)")
    deploy.add_argument("project", nargs="*")
    deploy.add_argument("--wait", action="store_true")
    deploy.add_argument("--timeout", default="5m")

    delete = sub.add_parser("delete", help="remove a project and its namespace")
    delete.add_argument("project", nargs="+")

    sub.add_parser("status", help="what is running, per project")

    build = sub.add_parser("build", help="build project images from their repositories")
    build.add_argument("project", nargs="*")
    build.add_argument("--load", action="store_true", help="load the image into a kind cluster")
    build.add_argument("--kind-cluster", default="poc-platform")

    bootstrap = sub.add_parser("bootstrap", help="create the cluster and install the ingress")
    bootstrap.add_argument("--target", choices=["local", "aks"], default="local")
    bootstrap.add_argument("--ingress-version", default="4.11.3")
    bootstrap.add_argument("--kind-cluster", default="poc-platform")

    new = sub.add_parser("new", help="scaffold a project file from the template")
    new.add_argument("id")

    return parser


COMMANDS = {
    "list": cmd_list,
    "render": cmd_render,
    "deploy": cmd_deploy,
    "delete": cmd_delete,
    "status": cmd_status,
    "build": cmd_build,
    "bootstrap": cmd_bootstrap,
    "new": cmd_new,
}


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    for tool in ("helm", "kubectl"):
        if args.command not in ("list", "new") and shutil.which(tool) is None:
            print(f"{tool} is not installed", file=sys.stderr)
            return 2
    try:
        return COMMANDS[args.command](args, Platform.load())
    except (Failure, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
