"""The read path a client SDK would call to resolve a flag for one user."""

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_service
from app.models import EvaluationResult
from app.services import FlagService
from app.targeting import evaluate

router = APIRouter(tags=["evaluation"])


@router.get("/api/evaluate/{name}", response_model=EvaluationResult)
def evaluate_flag(
    name: str,
    user_id: str = Query(default="anonymous"),
    team: str = Query(default=""),
    service: FlagService = Depends(get_service),
) -> EvaluationResult:
    """Resolve `name` for a user, returning the value and why it was chosen."""
    return evaluate(service.get_by_name(name), user_id=user_id, team=team)
