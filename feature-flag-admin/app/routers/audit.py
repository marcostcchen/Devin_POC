"""Audit history: per flag, or the global activity feed."""

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_service
from app.models import AuditEntry
from app.services import FlagService

router = APIRouter(tags=["audit"])


@router.get("/api/flags/{flag_id}/audit", response_model=list[AuditEntry])
def flag_audit(
    flag_id: int,
    limit: int = Query(default=100, ge=1, le=1000),
    service: FlagService = Depends(get_service),
) -> list[AuditEntry]:
    """History for one flag; survives the flag itself being deleted."""
    return service.history(flag_id=flag_id, limit=limit)


@router.get("/api/audit", response_model=list[AuditEntry])
def recent_activity(
    limit: int = Query(default=100, ge=1, le=1000),
    service: FlagService = Depends(get_service),
) -> list[AuditEntry]:
    return service.history(limit=limit)
