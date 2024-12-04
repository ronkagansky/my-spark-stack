from fastapi import APIRouter, Depends, HTTPException
from typing import List
import secrets
import datetime
from sqlalchemy.orm import Session

from db.models import User, TeamInvite, TeamMember, Team
from schemas.models import TeamResponse, TeamInviteResponse, TeamUpdate
from routers.auth import get_current_user_from_token
from db.database import get_db
from config import FRONTEND_URL

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.get("", response_model=List[TeamResponse])
async def get_user_teams(
    current_user: User = Depends(get_current_user_from_token),
):
    # Get teams through team_memberships relationship
    return [membership.team for membership in current_user.team_memberships]


@router.post("/{team_id}/invites", response_model=TeamInviteResponse)
async def generate_team_invite(
    team_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    # Check if user is member of team
    team_member = any(
        membership.team_id == team_id for membership in current_user.team_memberships
    )
    if not team_member:
        raise HTTPException(status_code=403, detail="Not a member of this team")

    token = secrets.token_urlsafe(32)

    invite = TeamInvite(
        team_id=team_id,
        created_by_id=current_user.id,
        invite_code=token,
        expires_at=datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(days=7),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    invite_link = f"{FRONTEND_URL}/invite/{token}"
    return TeamInviteResponse(invite_link=invite_link)


@router.post("/join/{invite_code}", response_model=TeamResponse)
async def join_team_with_invite(
    invite_code: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    # Find the invite
    invite = db.query(TeamInvite).filter(TeamInvite.invite_code == invite_code).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")

    # Check if invite is expired
    if invite.expires_at < datetime.datetime.now(datetime.timezone.utc):
        raise HTTPException(status_code=400, detail="Invite has expired")

    # Check if user is already a member of the team
    existing_membership = (
        db.query(TeamMember)
        .filter(
            TeamMember.team_id == invite.team_id,
            TeamMember.user_id == current_user.id,
        )
        .first()
    )
    if existing_membership:
        raise HTTPException(status_code=400, detail="Already a member of this team")

    # Create team membership
    membership = TeamMember(
        team_id=invite.team_id,
        user_id=current_user.id,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    # Return the team
    return membership.team


@router.patch("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    team_update: TeamUpdate,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    # Check if user is member of team
    team_member = any(
        membership.team_id == team_id for membership in current_user.team_memberships
    )
    if not team_member:
        raise HTTPException(status_code=403, detail="Not a member of this team")

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if team_update.name is not None:
        team.name = team_update.name

    db.commit()
    db.refresh(team)
    return team
