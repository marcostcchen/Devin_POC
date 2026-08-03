"""Persona resolution and the headers prototypes receive."""

import pytest

from platform_core.config import Principal
from platform_core.identity import ROLE_HEADER, USER_HEADER, IdentityService

PRINCIPALS = [
    Principal(
        email="ada@example.com",
        display_name="Ada Lovelace",
        platform_role="platform_admin",
        app_roles={"example-poc": "admin"},
    ),
    Principal(
        email="linus@example.com",
        display_name="Linus Park",
        platform_role="observer",
        app_roles={"example-poc": "editor"},
    ),
]


@pytest.fixture()
def service() -> IdentityService:
    return IdentityService(PRINCIPALS, "ada@example.com")


def test_unknown_cookie_falls_back_to_the_default_persona(service):
    assert service.get("nobody@example.com").email == "ada@example.com"
    assert service.get(None).email == "ada@example.com"


def test_role_is_mapped_per_app(service, manifest):
    assert service.resolve(PRINCIPALS[0], manifest).app_role == "admin"


def test_role_the_app_does_not_declare_degrades_to_its_default(service, manifest):
    # "editor" is configured for Linus but the manifest only knows admin/viewer.
    assert service.resolve(PRINCIPALS[1], manifest).app_role == "viewer"


def test_headers_carry_the_persona_and_its_app_role(service, manifest):
    headers = service.headers_for(PRINCIPALS[0], manifest, "req-1")
    assert headers[USER_HEADER] == "ada@example.com"
    assert headers[ROLE_HEADER] == "admin"


def test_config_drift_is_reported(service, manifest):
    problems = service.unknown_roles({"example-poc": manifest})
    assert problems == ["linus@example.com: role 'editor' is not declared by example-poc"]


def test_platform_config_maps_every_persona_to_real_roles(platform_config, repo_manifests):
    service = IdentityService(platform_config.principals, platform_config.default_principal)
    assert service.unknown_roles(repo_manifests) == []


def test_default_principal_must_exist():
    with pytest.raises(ValueError, match="default_principal"):
        IdentityService(PRINCIPALS, "ghost@example.com")
