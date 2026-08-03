"""Identity behind an authenticating proxy: groups in, roles out."""

import pytest

from app import auth

GROUP_ROLES = {"platform-admins": "admin", "feature-flag-admins": "admin"}


@pytest.fixture()
def proxied(client, monkeypatch):
    monkeypatch.setattr(auth, "PROXY_AUTH", True)
    monkeypatch.setattr(auth, "GROUP_ROLES", GROUP_ROLES)
    return client


def test_a_mapped_group_grants_the_role(monkeypatch):
    monkeypatch.setattr(auth, "GROUP_ROLES", GROUP_ROLES)
    assert auth.role_for_groups("something,feature-flag-admins") == "admin"


def test_an_unmapped_caller_gets_the_least_privilege(monkeypatch):
    monkeypatch.setattr(auth, "GROUP_ROLES", GROUP_ROLES)
    assert auth.role_for_groups("some-other-team") == "viewer"


def test_the_asserted_identity_is_used(proxied):
    me = proxied.get(
        "/api/me",
        headers={
            "X-Auth-Request-Email": "zoe@example.com",
            "X-Auth-Request-User": "Zoe Q",
            "X-Auth-Request-Groups": "platform-admins",
        },
    ).json()
    assert (me["email"], me["role"]) == ("zoe@example.com", "admin")


def test_a_viewer_still_cannot_write(proxied):
    response = proxied.post(
        "/api/flags",
        json={"name": "from-a-viewer"},
        headers={"X-Auth-Request-Email": "zoe@example.com", "X-Auth-Request-Groups": "guests"},
    )
    assert response.status_code == 403


def test_a_request_the_proxy_did_not_authenticate_is_rejected(proxied):
    # The local roster is not a fallback once something else owns identity.
    assert proxied.get("/api/me", headers={"X-User": "ada@example.com"}).status_code == 401
