"""Flag CRUD. Mutations require the admin role; reads are open to everyone."""

from fastapi import APIRouter, Depends

from app.auth import Actor, current_actor
from app.dependencies import get_service
from app.models import Flag, FlagCreate, FlagUpdate
from app.services import FlagService

router = APIRouter(prefix="/api/flags", tags=["flags"])


@router.get("", response_model=list[Flag])
def list_flags(service: FlagService = Depends(get_service)) -> list[Flag]:
    return service.list_flags()


@router.post("", response_model=Flag, status_code=201)
def create_flag(
    payload: FlagCreate,
    actor: Actor = Depends(current_actor),
    service: FlagService = Depends(get_service),
) -> Flag:
    return service.create(payload, actor)


@router.patch("/{flag_id}", response_model=Flag)
def update_flag(
    flag_id: int,
    payload: FlagUpdate,
    actor: Actor = Depends(current_actor),
    service: FlagService = Depends(get_service),
) -> Flag:
    return service.update(flag_id, payload, actor)


@router.delete("/{flag_id}", status_code=204)
def delete_flag(
    flag_id: int,
    actor: Actor = Depends(current_actor),
    service: FlagService = Depends(get_service),
) -> None:
    service.delete(flag_id, actor)
