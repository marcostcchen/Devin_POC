"""Environment policy: the rules a prototype must satisfy to be hosted here.

The interesting half of a POC platform is not what it runs but what it refuses
to run. `policy.yaml` states the guardrails once; `check_manifest` turns the
enforceable subset into per-app violations that the console surfaces and the
supervisor honours.
"""

import os
from typing import Optional

import yaml
from pydantic import BaseModel, Field

from platform_core.manifest import Manifest

POLICY_FILENAME = "policy.yaml"


class Limits(BaseModel):
    """The machine-checkable rules."""

    data_classifications: list[str]
    data_stores: list[str]
    identity_modes: list[str]
    stages: list[str]
    min_limitations: int = 1


class Guardrail(BaseModel):
    """One human-facing rule, rendered in the console."""

    title: str
    detail: str
    #: For a "not allowed" rule: the sanctioned way to get the same demo value.
    instead: Optional[str] = None


class Policy(BaseModel):
    """Everything `policy.yaml` says about this environment."""

    environment: str
    limits: Limits
    allowed: list[Guardrail] = Field(default_factory=list)
    not_allowed: list[Guardrail] = Field(default_factory=list)

    def check_manifest(self, manifest: Manifest) -> list[str]:
        """Return the policy violations in `manifest` (empty means compliant)."""
        violations: list[str] = []

        if manifest.stage not in self.limits.stages:
            violations.append(
                f"stage {manifest.stage!r} is not one of {self.limits.stages}: "
                "this environment only hosts prototypes"
            )
        if manifest.data.classification not in self.limits.data_classifications:
            violations.append(
                f"data.classification {manifest.data.classification!r} is not one of "
                f"{self.limits.data_classifications}: real data may not be used here"
            )
        if manifest.data.store not in self.limits.data_stores:
            violations.append(
                f"data.store {manifest.data.store!r} is not one of {self.limits.data_stores}: "
                "prototypes keep their state local and disposable"
            )
        if manifest.identity.mode not in self.limits.identity_modes:
            violations.append(
                f"identity.mode {manifest.identity.mode!r} is not one of "
                f"{self.limits.identity_modes}: identity is always mocked here"
            )
        if len(manifest.limitations) < self.limits.min_limitations:
            violations.append(
                f"only {len(manifest.limitations)} limitation(s) declared, at least "
                f"{self.limits.min_limitations} required: say what the prototype fakes"
            )

        return violations


def load_policy(path: str) -> Policy:
    """Read `policy.yaml` from disk."""
    with open(path, "r", encoding="utf-8") as handle:
        return Policy.model_validate(yaml.safe_load(handle))


def default_policy_path(platform_dir: str) -> str:
    return os.path.join(platform_dir, POLICY_FILENAME)
