from typing import Optional

from pydantic import BaseModel, Field, field_validator


class FlagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    enabled: bool = False
    rollout_percentage: int = 100
    target_team: str = ""

    @field_validator("name")
    @classmethod
    def slugish(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        return v

    @field_validator("rollout_percentage")
    @classmethod
    def in_range(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("rollout_percentage must be between 0 and 100")
        return v


class FlagUpdate(BaseModel):
    description: Optional[str] = None
    enabled: Optional[bool] = None
    rollout_percentage: Optional[int] = None
    target_team: Optional[str] = None

    @field_validator("rollout_percentage")
    @classmethod
    def in_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not 0 <= v <= 100:
            raise ValueError("rollout_percentage must be between 0 and 100")
        return v


class Flag(BaseModel):
    id: int
    name: str
    description: str
    enabled: bool
    rollout_percentage: int
    target_team: str
    created_at: str
    updated_at: str


class AuditEntry(BaseModel):
    id: int
    flag_id: int
    flag_name: str
    actor: str
    action: str
    detail: str
    created_at: str


class EvaluationResult(BaseModel):
    flag: str
    user_id: str
    team: str
    enabled: bool
    reason: str
