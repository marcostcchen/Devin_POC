"""Who am I, and who else can I act as."""

from fastapi import APIRouter, Depends

from app.auth import Actor, current_actor
from app.config import PROXY_AUTH, USERS
from app.models import Identity

router = APIRouter(tags=["identity"])


@router.get("/api/me", response_model=Identity)
def me(actor: Actor = Depends(current_actor)) -> Identity:
    """Return the acting identity plus the roster the UI's switcher renders."""
    return Identity(
        email=actor.email,
        role=actor.role,
        # Behind a proxy the identity is not ours to change, so there is nothing
        # local to switch between.
        users={} if PROXY_AUTH else USERS,
        display_name=actor.display_name,
        proxy_auth=PROXY_AUTH,
    )
