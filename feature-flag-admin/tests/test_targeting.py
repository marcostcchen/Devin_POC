"""Unit tests for the pure evaluation logic."""

from app.models import Flag
from app.targeting import bucket_of, evaluate


def make_flag(**overrides) -> Flag:
    values = {
        "id": 1,
        "name": "demo",
        "description": "",
        "enabled": True,
        "rollout_percentage": 100,
        "target_team": "",
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    }
    return Flag(**{**values, **overrides})


def test_bucket_is_sticky_and_flag_scoped():
    assert bucket_of("demo", "user-1") == bucket_of("demo", "user-1")
    assert 0 <= bucket_of("demo", "user-1") < 100
    assert bucket_of("demo", "user-1") != bucket_of("other", "user-1")


def test_disabled_flag_short_circuits():
    result = evaluate(make_flag(enabled=False, rollout_percentage=100), "user-1", "")
    assert result.enabled is False and result.reason == "flag disabled"


def test_team_targeting_requires_a_match():
    flag = make_flag(target_team="platform")
    assert evaluate(flag, "user-1", "web").enabled is False
    assert evaluate(flag, "user-1", "platform").enabled is True


def test_rollout_bounds():
    assert evaluate(make_flag(rollout_percentage=0), "user-1", "").enabled is False
    assert evaluate(make_flag(rollout_percentage=100), "user-1", "").enabled is True


def test_rollout_only_ever_adds_users_as_it_grows():
    flag_name = "demo"
    users = [f"user-{i}" for i in range(200)]
    at_50 = {u for u in users if bucket_of(flag_name, u) < 50}
    at_80 = {u for u in users if bucket_of(flag_name, u) < 80}
    assert at_50 < at_80
