"""The `poc.yaml` manifest: how a prototype describes itself to the platform.

Every prototype in this repository ships one manifest at its root. The platform
never guesses how to run an app, which roles it understands or what it fakes —
all of that is declared here and validated on load.
"""

from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

MANIFEST_FILENAME = "poc.yaml"
SCHEMA_VERSION = 1


class RuntimeSpec(BaseModel):
    """How the platform starts and health-checks the app."""

    #: Shell command run from the app directory. Must honour `$PORT`.
    command: str
    #: Port the app listens on, both standalone and under the platform.
    port: int = Field(ge=1024, le=65535)
    #: Path the platform polls (relative to the app root) to decide it is up.
    health_path: str = "/healthz"
    #: How long a cold start may take, including dependency installation.
    ready_timeout_seconds: int = Field(default=300, ge=5, le=1800)

    @field_validator("health_path")
    @classmethod
    def _leading_slash(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("health_path must start with '/'")
        return value


class IdentitySpec(BaseModel):
    """Which roles the app understands and how it learns who is calling."""

    #: Only mocked, header-based identity is allowed in this environment.
    mode: Literal["platform-headers"]
    roles: list[str] = Field(min_length=1)
    #: Role assumed when the platform sends no role (standalone runs).
    default_role: str

    @model_validator(mode="after")
    def _default_role_is_known(self) -> "IdentitySpec":
        if self.default_role not in self.roles:
            raise ValueError(f"default_role {self.default_role!r} is not in roles {self.roles}")
        return self


class DataSpec(BaseModel):
    """What the app stores, and how throwaway it is."""

    classification: str
    store: str
    #: Optional command that wipes local state back to the seeded dataset.
    reset_command: Optional[str] = None


class Manifest(BaseModel):
    """A prototype's platform contract."""

    schema_version: Literal[SCHEMA_VERSION]
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,40}$")
    name: str
    summary: str
    owner: str
    stage: str
    stack: list[str] = Field(min_length=1)
    runtime: RuntimeSpec
    identity: IdentitySpec
    data: DataSpec
    #: Plain-language statements of what the prototype does demonstrate...
    capabilities: list[str] = Field(min_length=1)
    #: ...and what it deliberately fakes or leaves out.
    limitations: list[str] = Field(min_length=1)
    docs: list[str] = Field(default_factory=list)

    @property
    def base_path(self) -> str:
        """Path the gateway serves this app under."""
        return f"/apps/{self.id}"


class ManifestError(Exception):
    """A manifest is missing, unparseable or invalid."""


def load_manifest(path: str) -> Manifest:
    """Read and validate a single `poc.yaml`."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
    except FileNotFoundError as exc:
        raise ManifestError(f"no manifest at {path}") from exc
    except yaml.YAMLError as exc:
        raise ManifestError(f"{path} is not valid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise ManifestError(f"{path} must contain a YAML mapping")

    try:
        return Manifest.model_validate(raw)
    except Exception as exc:  # pydantic ValidationError, re-raised with the file name
        raise ManifestError(f"{path} is not a valid manifest: {exc}") from exc
