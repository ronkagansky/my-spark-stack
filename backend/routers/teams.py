from fastapi import APIRouter, Depends
from typing import List

from db.models import User
from schemas.models import TeamResponse
from routers.auth import get_current_user_from_token

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.get("", response_model=List[TeamResponse])
async def get_user_teams(
    current_user: User = Depends(get_current_user_from_token),
):
    # Get teams through team_memberships relationship
    return [membership.team for membership in current_user.team_memberships]
