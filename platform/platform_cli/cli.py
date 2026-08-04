"""`platformctl` — deploy a project onto the platform, or take it away again.

Every command is a thin wrapper over helm/kubectl/docker: there is no state
here and nothing to run in the background. The unit of work is a project file,
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
from platform_cli.policy import Policy, cross_violations
from platform_cli.render import app_values, portal_values

APP_CHART = CHARTS_DIR / "poc-app"
PORTAL_CHART = CHARTS_DIR / "poc-portal"
BOOTSTRAP_DIR = CHARTS_DIR.parent / "bootstrap"


class Failure(Exception):
    """Something the user has to fix; printed without a traceback."""


def run(command: Sequence[str], capture: bool = False, stdin: str | None = None) -> str:
    printable = " ".join(command)
    if not capture:
        print(f"$ {printable}", file=sys.stderr)
    result = subprocess.run(command, capture_output=capture, text=True, input=stdin)
    if result.returncode != 0:
        raise Failure(f"command failed: {printable}\n{result.stderr or ''}".rstrip())
    return result.stdout if capture else ""


def ensure_system_namespace(platform: Platform) -> None:
    """Create the platform namespace, which holds every release's own state.

    A project's namespace is created *by* its release, so it cannot also be the
    namespace Helm keeps that release in; all releases live here instead.
    """
    manifest = yaml.safe_load((BOOTSTRAP_DIR / "system-namespace.yaml").read_text("utf-8"))
    manifest["metadata"]["name"] = platform.system_namespace
    run(["kubectl", "apply", "-f", "-"], stdin=yaml.safe_dump(manifest))


def _values_file(values: Dict[str, Any], stack: List[str]) -> str:
    handle = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
    yaml.safe_dump(values, handle, sort_keys=False)
    handle.close()
    stack.append(handle.name)
    return handle.name


def _selected(platform: Platform, ids: Sequence[str]) -> List[Project]:
    if not ids:
        return load_projects()
    return [load_project(project_id) for project_id in ids]


def _check(platform: Platform, policy: Policy, projects: Sequence[Project]) -> None:
    problems: List[str] = []
    for project in projects:
        problems += [f"{project.id}: {issue}" for issue in policy.violations(project, platform)]
    problems += cross_violations(load_projects())
    if problems:
        raise Failure("policy violations:\n  - " + "\n  - ".join(problems))


# --- commands ---------------------------------------------------------------


def cmd_list(args: argparse.Namespace, platform: Platform, policy: Policy) -> int:
    rows = []
    for project in load_projects():
        issues = policy.violations(project, platform)
        rows.append(
            (
                project.id,
                platform.namespace(project.id),
                platform.url(project.subdomain),
                project.section("runtime").get("size", "?"),
                "ok" if not issues else f"{len(issues)} policy issue(s)",
            )
        )
    widths = [max(len(row[i]) for row in rows + [("PROJECT", "NAMESPACE", "URL", "SIZE", "POLICY")])
              for i in range(5)]
    header = ("PROJECT", "NAMESPACE", "URL", "SIZE", "POLICY")
    for row in [header, *rows]:
        print("  ".join(value.ljust(widths[i]) for i, value in enumerate(row)).rstrip())
    return 0


def cmd_validate(args: argparse.Namespace, platform: Platform, policy: Policy) -> int:
    projects = _selected(platform, args.project)
    _check(platform, policy, projects)
    print(f"{len(projects)} project(s) valid against policy.yaml")
    return 0


def cmd_render(args: argparse.Namespace, platform: Platform, policy: Policy) -> int:
    if args.portal:
        values = portal_values(platform, load_projects(), policy)
        chart, release = PORTAL_CHART, "poc-portal"
    else:
        project = load_project(args.project[0])
        values = app_values(project, platform)
        chart, release = APP_CHART, project.id
    namespace = platform.system_namespace
    temp: List[str] = []
    try:
        print(
            run(
                [
                    "helm", "template", release, str(chart),
                    "--namespace", namespace,
                    "--values", _values_file(values, temp),
                ],
                capture=True,
            )
        )
    finally:
        for path in temp:
            Path(path).unlink(missing_ok=True)
    return 0


def cmd_deploy(args: argparse.Namespace, platform: Platform, policy: Policy) -> int:
    projects = _selected(platform, args.project)
    _check(platform, policy, projects)
    ensure_system_namespace(platform)
    temp: List[str] = []
    try:
        for project in projects:
            command = [
                "helm", "upgrade", "--install", project.id, str(APP_CHART),
                "--namespace", platform.system_namespace,
                "--values", _values_file(app_values(project, platform), temp),
            ]
            if args.wait:
                command += ["--wait", "--timeout", args.timeout]
            run(command)
        # The portal's catalog is derived from every project file, so it is
        # refreshed on every deploy: publishing a project is not a second step.
        run(
            [
                "helm", "upgrade", "--install", "poc-portal", str(PORTAL_CHART),
                "--namespace", platform.system_namespace,
                "--values", _values_file(portal_values(platform, load_projects(), policy), temp),
            ]
        )
    finally:
        for path in temp:
            Path(path).unlink(missing_ok=True)
    print(f"\ndeployed: {', '.join(platform.url(p.subdomain) for p in projects)}")
    print(f"portal:   {platform.url('portal')}")
    return 0


def cmd_delete(args: argparse.Namespace, platform: Platform, policy: Policy) -> int:
    for project_id in args.project:
        run(["helm", "uninstall", project_id, "--namespace", platform.system_namespace])
        # The namespace belongs to the release, so this is the whole cleanup.
        print(f"{project_id}: namespace {platform.namespace(project_id)} removed")
    return 0


def cmd_restart(args: argparse.Namespace, platform: Platform, policy: Policy) -> int:
    for project_id in args.project:
        run(
            [
                "kubectl", "rollout", "restart", f"deployment/{project_id}",
                "--namespace", platform.namespace(project_id),
            ]
        )
        print(f"{project_id}: restarted; ephemeral data is reseeded on the new pod")
    return 0


def cmd_status(args: argparse.Namespace, platform: Platform, policy: Policy) -> int:
    for project in load_projects():
        namespace = platform.namespace(project.id)
        pods = run(
            ["kubectl", "get", "pods", "--namespace", namespace, "-o", "json"], capture=True
        )
        items = json.loads(pods or "{}").get("items", [])
        states = [
            f"{pod['metadata']['name']} {pod['status'].get('phase', '?')}"
            + ("" if _ready(pod) else " (not ready)")
            for pod in items
        ] or ["not deployed"]
        print(f"{project.id:<24} {platform.url(project.subdomain):<44} {'; '.join(states)}")
    return 0


def _ready(pod: Dict[str, Any]) -> bool:
    return all(
        status.get("ready")
        for status in pod.get("status", {}).get("containerStatuses", [])
    )


def cmd_build(args: argparse.Namespace, platform: Platform, policy: Policy) -> int:
    targets: List[tuple[str, Path]] = []
    if args.portal or not args.project:
        targets.append(("poc/poc-portal:0.1.0", (CHARTS_DIR.parent / "portal")))
    for project in _selected(platform, args.project) if not args.portal else []:
        path = project.repo_path
        if path is None or not path.exists():
            raise Failure(f"{project.id}: repo {project.raw.get('repo')!r} is not a local path")
        image = project.section("image")
        targets.append((f"{image['repository']}:{image['tag']}", path))

    for tag, context in targets:
        run(["docker", "build", "-t", tag, str(context)])
        if args.load:
            run(["kind", "load", "docker-image", tag, "--name", args.kind_cluster])
    return 0


def cmd_bootstrap(args: argparse.Namespace, platform: Platform, policy: Policy) -> int:
    values = BOOTSTRAP_DIR / f"ingress-nginx.{args.target}.yaml"
    run(["helm", "repo", "add", "ingress-nginx", "https://kubernetes.github.io/ingress-nginx"])
    run(["helm", "repo", "update", "ingress-nginx"])
    run(
        [
            "helm", "upgrade", "--install", "ingress-nginx", "ingress-nginx/ingress-nginx",
            "--version", args.ingress_version,
            "--namespace", "ingress-nginx", "--create-namespace",
            "--values", str(values), "--wait", "--timeout", "5m",
        ]
    )
    ensure_system_namespace(platform)
    temp: List[str] = []
    try:
        run(
            [
                "helm", "upgrade", "--install", "poc-portal", str(PORTAL_CHART),
                "--namespace", platform.system_namespace,
                "--values", _values_file(portal_values(platform, load_projects(), policy), temp),
                "--wait", "--timeout", "5m",
            ]
        )
    finally:
        for path in temp:
            Path(path).unlink(missing_ok=True)
    print(f"portal: {platform.url('portal')}")
    return 0


def cmd_new(args: argparse.Namespace, platform: Platform, policy: Policy) -> int:
    destination = PROJECTS_DIR / f"{args.id}.yaml"
    if destination.exists():
        raise Failure(f"{destination} already exists")
    text = (PROJECTS_DIR / "_template.yaml").read_text(encoding="utf-8")
    # The template's header addresses whoever is copying it by hand; a scaffolded
    # file starts at the schema instead.
    body = text[text.index("schema_version:"):]
    destination.write_text(body.replace("my-project", args.id), encoding="utf-8")
    print(f"created {destination}\nedit it, then: ./platformctl validate && ./platformctl deploy {args.id}")
    return 0


# --- entrypoint -------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="platformctl", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="every project, its namespace, its URL and its policy state")

    validate = sub.add_parser("validate", help="check project files against policy.yaml")
    validate.add_argument("project", nargs="*")

    render = sub.add_parser("render", help="print the Kubernetes manifests for a project")
    render.add_argument("project", nargs="*")
    render.add_argument("--portal", action="store_true", help="render the platform portal instead")

    deploy = sub.add_parser("deploy", help="install or upgrade projects (all of them by default)")
    deploy.add_argument("project", nargs="*")
    deploy.add_argument("--wait", action="store_true")
    deploy.add_argument("--timeout", default="5m")

    delete = sub.add_parser("delete", help="remove a project and its namespace")
    delete.add_argument("project", nargs="+")

    restart = sub.add_parser("restart", help="restart a project, resetting ephemeral data")
    restart.add_argument("project", nargs="+")

    sub.add_parser("status", help="what is running, per project")

    build = sub.add_parser("build", help="build project images from their repositories")
    build.add_argument("project", nargs="*")
    build.add_argument("--portal", action="store_true", help="build the portal image only")
    build.add_argument("--load", action="store_true", help="load the image into a kind cluster")
    build.add_argument("--kind-cluster", default="poc-platform")

    bootstrap = sub.add_parser("bootstrap", help="install the ingress controller and the portal")
    bootstrap.add_argument("--target", choices=["local", "aks"], default="local")
    bootstrap.add_argument("--ingress-version", default="4.11.3")

    new = sub.add_parser("new", help="scaffold a project file from the template")
    new.add_argument("id")

    return parser


COMMANDS = {
    "list": cmd_list,
    "validate": cmd_validate,
    "render": cmd_render,
    "deploy": cmd_deploy,
    "delete": cmd_delete,
    "restart": cmd_restart,
    "status": cmd_status,
    "build": cmd_build,
    "bootstrap": cmd_bootstrap,
    "new": cmd_new,
}


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    for tool in ("helm", "kubectl"):
        if args.command not in ("list", "validate", "new") and shutil.which(tool) is None:
            print(f"{tool} is not installed", file=sys.stderr)
            return 2
    try:
        return COMMANDS[args.command](args, Platform.load(), Policy.load())
    except (Failure, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
