"""Pure flag evaluation: given a flag and a user context, is it on?

Kept free of database and HTTP concerns so the rollout maths can be reasoned
about (and tested) on its own.
"""

import hashlib

from app.models import EvaluationResult, Flag

BUCKETS = 100


def bucket_of(flag_name: str, user_id: str) -> int:
    """Return a stable bucket in [0, 100) for a (flag, user) pair.

    Hashing the pair — rather than the user alone — keeps a user's assignment
    sticky across evaluations while staying independent per flag, so raising a
    rollout only ever adds users and two flags at 10% do not hit the same ones.
    """
    digest = hashlib.sha256(f"{flag_name}:{user_id}".encode()).hexdigest()
    return int(digest[:8], 16) % BUCKETS


def evaluate(flag: Flag, user_id: str, team: str) -> EvaluationResult:
    """Resolve `flag` for one user, explaining the outcome via `reason`.

    Checks are ordered cheapest-and-broadest first: the global switch, then the
    team restriction, then the percentage rollout.
    """

    def result(enabled: bool, reason: str) -> EvaluationResult:
        return EvaluationResult(
            flag=flag.name, user_id=user_id, team=team, enabled=enabled, reason=reason
        )

    if not flag.enabled:
        return result(False, "flag disabled")
    if flag.target_team and flag.target_team != team:
        return result(False, f"targeted at team '{flag.target_team}'")

    bucket = bucket_of(flag.name, user_id)
    within = bucket < flag.rollout_percentage
    position = "within" if within else "outside"
    return result(within, f"bucket {bucket} {position} {flag.rollout_percentage}% rollout")
