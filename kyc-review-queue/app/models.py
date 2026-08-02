from typing import Literal

from pydantic import BaseModel, Field, field_validator

RiskLevel = Literal["low", "medium", "high"]
CaseStatus = Literal["new", "in_review", "escalated", "closed"]
DecisionAction = Literal["approve", "reject", "escalate", "claim"]


class Case(BaseModel):
    id: int
    reference: str
    customer_name: str
    country: str
    document_type: str
    document_number: str
    risk_level: RiskLevel
    status: CaseStatus
    documents: list[str]
    created_at: str
    updated_at: str


class DecisionCreate(BaseModel):
    action: DecisionAction
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason")
    @classmethod
    def non_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("reason is required")
        return v


class DecisionEntry(BaseModel):
    id: int
    case_id: int
    case_reference: str
    actor: str
    actor_role: str
    action: str
    reason: str
    status_before: str
    status_after: str
    created_at: str
