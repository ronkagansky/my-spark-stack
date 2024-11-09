from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt, JWTError
import secrets
import os

from db.database import get_db
from db.models import User
from schemas.models import UserCreate, UserResponse, AuthResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
API_KEY_HEADER = APIKeyHeader(name="Authorization")


async def get_current_user_from_token(
    token: str = Security(API_KEY_HEADER), db: Session = Depends(get_db)
):
    try:
        # Remove 'Bearer ' prefix if present
        token = token.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/create", response_model=AuthResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user or return existing user with the given username"""
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        # If user exists, generate new token and return
        token = jwt.encode(
            {
                "sub": existing_user.username,
                "exp": datetime.utcnow() + timedelta(days=30),
            },
            SECRET_KEY,
            algorithm="HS256",
        )
        return AuthResponse(user=existing_user, token=token)

    # Create new user
    new_user = User(username=user.username)
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
        # Generate token for new user
        token = jwt.encode(
            {"sub": new_user.username, "exp": datetime.utcnow() + timedelta(days=30)},
            SECRET_KEY,
            algorithm="HS256",
        )
        return AuthResponse(user=new_user, token=token)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: User = Depends(get_current_user_from_token)):
    return current_user
