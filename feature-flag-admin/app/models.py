"""Request and response schemas shared by the API and the React client."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

ROLLOUT_ERROR = "rollout_percentage must be between 0 and 100"


class FlagCreate(BaseModel):
    """Payload for `POST /api/flags`."""

    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    enabled: bool = False
    rollout_percentage: int = 100
    target_team: str = ""

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be empty")
        return value

    @field_validator("rollout_percentage")
    @classmethod
    def check_rollout(cls, value: int) -> int:
        if not 0 <= value <= 100:
            raise ValueError(ROLLOUT_ERROR)
        return value


class FlagUpdate(BaseModel):
    """Partial update for `PATCH /api/flags/{id}`; unset fields are untouched."""

    description: Optional[str] = None
    enabled: Optional[bool] = None
    rollout_percentage: Optional[int] = None
    target_team: Optional[str] = None

    @field_validator("rollout_percentage")
    @classmethod
    def check_rollout(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and not 0 <= value <= 100:
            raise ValueError(ROLLOUT_ERROR)
        return value


class Flag(BaseModel):
    """A feature flag as stored and returned by the API."""

    id: int
    name: str
    description: str
    enabled: bool
    rollout_percentage: int
    target_team: str
    created_at: str
    updated_at: str


class AuditEntry(BaseModel):
    """One immutable record of who changed what, and when."""

    id: int
    flag_id: int
    flag_name: str
    actor: str
    action: str
    detail: str
    created_at: str


class Identity(BaseModel):
    """The acting user, plus every identity the UI may switch to."""

    email: str
    role: str
    users: dict[str, str]


class EvaluationResult(BaseModel):
    """A flag resolved for one user, with a human-readable justification."""

    flag: str
    user_id: str
    team: str
    enabled: bool
    reason: str
