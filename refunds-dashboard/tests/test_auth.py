"""Identity behind an authenticating proxy: groups in, roles out."""

import os
import tempfile

os.environ.setdefault("REFUNDS_DB_PATH", os.path.join(tempfile.mkdtemp(), "auth.db"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import auth  # noqa: E402
from app.main import app  # noqa: E402

GROUP_ROLES = {"refunds-finance": "finance_approver", "refunds-agents": "support_agent"}


@pytest.fixture()
def proxied(monkeypatch):
    monkeypatch.setattr(auth, "PROXY_AUTH", True)
    monkeypatch.setattr(auth, "GROUP_ROLES", GROUP_ROLES)
    with TestClient(app) as client:
        yield client


def test_the_first_mapped_group_decides(monkeypatch):
    monkeypatch.setattr(auth, "GROUP_ROLES", GROUP_ROLES)
    assert auth.role_for_groups("refunds-agents,refunds-finance") == "finance_approver"
    assert auth.role_for_groups("refunds-agents") == "support_agent"


def test_an_unmapped_caller_gets_the_least_privilege(monkeypatch):
    monkeypatch.setattr(auth, "GROUP_ROLES", GROUP_ROLES)
    assert auth.role_for_groups("some-other-team") == "support_agent"


def test_the_asserted_identity_is_used(proxied):
    me = proxied.get(
        "/api/me",
        headers={
            "X-Auth-Request-Email": "dana@example.com",
            "X-Auth-Request-User": "Dana F",
            "X-Auth-Request-Groups": "refunds-finance",
        },
    ).json()
    assert (me["email"], me["role"], me["display_name"]) == (
        "dana@example.com",
        "finance_approver",
        "Dana F",
    )


def test_a_request_the_proxy_did_not_authenticate_is_rejected(proxied):
    # The local roster is not a fallback once something else owns identity.
    assert proxied.get("/api/me", headers={"X-User": "dana@example.com"}).status_code == 401
