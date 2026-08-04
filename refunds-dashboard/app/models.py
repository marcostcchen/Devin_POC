from typing import Literal

from pydantic import BaseModel, Field, field_validator

RefundStatus = Literal["pending", "approved", "denied", "processed"]
ReasonCode = Literal[
    "damaged_item",
    "not_delivered",
    "wrong_item",
    "late_delivery",
    "duplicate_charge",
    "changed_mind",
]
Decision = Literal["approve", "deny"]

REASON_CODES = list(ReasonCode.__args__)
STATUSES = list(RefundStatus.__args__)


class RefundRequest(BaseModel):
    id: int
    customer_name: str
    order_id: str
    amount: float
    reason_code: str
    status: RefundStatus
    requested_by: str
    created_at: str
    updated_at: str
    requires_finance_approval: bool


class RefundRequestCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    order_id: str = Field(min_length=1, max_length=40)
    amount: float = Field(gt=0, le=100_000)
    reason_code: ReasonCode


class Reasoned(BaseModel):
    """Every state change is explained; five characters is the floor."""

    reason: str = Field(min_length=5, max_length=1000)

    @field_validator("reason")
    @classmethod
    def non_blank(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 5:
            raise ValueError("reason must be at least 5 characters")
        return v


class DecisionCreate(Reasoned):
    decision: Decision


class ProcessCreate(Reasoned):
    pass


class AuditEvent(BaseModel):
    id: int
    refund_request_id: int
    order_id: str
    action: str
    reason: str
    actor: str
    actor_role: str
    status_before: str
    status_after: str
    created_at: str


class Metrics(BaseModel):
    total_requests: int
    counts_by_status: dict[str, int]
    total_refunded_amount: float
    total_approved_amount: float
    pending_amount: float
    pending_count: int
    average_request_amount: float
