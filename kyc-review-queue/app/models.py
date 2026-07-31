from typing import Literal

from pydantic import BaseModel, Field, field_validator

RiskLevel = Literal["low", "medium", "high"]
CaseStatus = Literal["new", "in_review", "escalated", "closed"]
Decision = Literal["approve", "reject", "escalate"]


class CaseSummary(BaseModel):
    id: int
    reference: str
    customer_name: str
    customer_ref: str
    jurisdiction: str
    risk_level: RiskLevel
    risk_note: str
    status: CaseStatus
    outcome: str
    submitted_at: str
    updated_at: str


class CaseDocument(BaseModel):
    id: int
    case_id: int
    doc_type: str
    filename: str
    received_at: str


class CaseEvent(BaseModel):
    id: int
    case_id: int
    case_reference: str
    actor: str
    actor_role: str
    action: str
    reason: str
    created_at: str


class CaseDetail(CaseSummary):
    document_number: str
    documents: list[CaseDocument]
    history: list[CaseEvent]


class DecisionRequest(BaseModel):
    decision: Decision
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason")
    @classmethod
    def non_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("a reason is required for every decision")
        return v
