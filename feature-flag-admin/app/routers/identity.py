"""Who am I, and who else can I act as."""

from fastapi import APIRouter, Depends

from app.auth import Actor, current_actor
from app.config import PLATFORM_MANAGED, USERS
from app.models import Identity

router = APIRouter(tags=["identity"])


@router.get("/api/me", response_model=Identity)
def me(actor: Actor = Depends(current_actor)) -> Identity:
    """Return the acting identity plus the roster the UI's switcher renders."""
    return Identity(
        email=actor.email,
        role=actor.role,
        # Under the platform the roster lives in the console, so there is
        # nothing local to switch between.
        users={} if PLATFORM_MANAGED else USERS,
        display_name=actor.display_name,
        platform_managed=PLATFORM_MANAGED,
        platform_console_url="/" if PLATFORM_MANAGED else "",
    )
