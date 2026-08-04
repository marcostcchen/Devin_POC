"""The rules that decide whether a project may be deployed at all."""

from platform_cli.config import Project
from platform_cli.policy import cross_violations


def test_the_projects_in_this_repository_comply(projects, policy, platform):
    for project in projects:
        assert policy.violations(project, platform) == [], project.id


def test_a_moving_image_tag_is_rejected(project_file, policy, platform):
    problems = policy.violations(project_file(image={"tag": "latest"}), platform)
    assert any("not pinned" in problem for problem in problems)


def test_real_data_is_rejected(project_file, policy, platform):
    problems = policy.violations(project_file(data={"classification": "production"}), platform)
    assert any("data.classification" in problem for problem in problems)


def test_a_production_stage_is_rejected(project_file, policy, platform):
    problems = policy.violations(project_file(stage="production"), platform)
    assert any("stage" in problem for problem in problems)


def test_credential_shaped_configuration_is_rejected(project_file, policy, platform):
    problems = policy.violations(
        project_file(runtime={"env": {"DATABASE_PASSWORD": "hunter2"}}), platform
    )
    assert any("credential" in problem for problem in problems)


def test_a_default_role_outside_the_declared_roles_is_rejected(project_file, policy, platform):
    problems = policy.violations(project_file(access={"default_role": "admin"}), platform)
    assert any("default_role" in problem for problem in problems)


def test_a_group_mapped_to_an_unknown_role_is_rejected(project_file, policy, platform):
    problems = policy.violations(
        project_file(access={"group_roles": {"platform-admins": "root"}}), platform
    )
    assert any("unknown role" in problem for problem in problems)


def test_storage_above_the_ceiling_is_rejected(project_file, policy, platform):
    problems = policy.violations(project_file(data={"persistence": "50Gi"}), platform)
    assert any("ceiling" in problem for problem in problems)


def test_too_many_replicas_are_rejected(project_file, policy, platform):
    problems = policy.violations(project_file(runtime={"replicas": 9}), platform)
    assert any("replicas" in problem for problem in problems)


def test_a_capability_that_parsed_as_a_dict_is_rejected(project_file, policy, platform):
    # An unquoted colon in the YAML makes the item a one-key dict, not a string.
    problems = policy.violations(
        project_file(capabilities=[{"Amount threshold": "finance only"}]), platform
    )
    assert any("capabilities must be a list of strings" in problem for problem in problems)


def test_two_projects_cannot_share_a_hostname(project_file):
    one = project_file(id="one", route={"subdomain": "same"})
    two = project_file(id="two", route={"subdomain": "same"})
    assert any("route.subdomain" in problem for problem in cross_violations([one, two]))


def test_the_file_name_must_match_the_id(tmp_path, policy, platform):
    path = tmp_path / "wrong-name.yaml"
    path.write_text("schema_version: 2\nid: right-name\n", encoding="utf-8")
    problems = policy.violations(Project.load(path), platform)
    assert any("file name" in problem for problem in problems)
