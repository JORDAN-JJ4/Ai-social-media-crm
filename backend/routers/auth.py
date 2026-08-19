import hashlib
import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from backend.database import get_db
from backend.models import User

from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, Header, Request

router = APIRouter(prefix="/api/auth", tags=["User Authentication"])

class UserSignup(BaseModel):
    email: str
    password: str
    full_name: str = "Growth Manager"

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

def _hash_password(password: str) -> str:
    salt = "synapse_growth_salt_2026"
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

@router.post("/signup", response_model=UserResponse)
def signup(payload: UserSignup, response: Response, db = Depends(get_db)):
    email = payload.email.strip().lower()
    if len(payload.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters long.")

    stmt = select(User).where(User.email == email)
    res = db.execute(stmt)
    existing = res.scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    hashed = _hash_password(payload.password)
    user = User(
        email=email,
        hashed_password=hashed,
        full_name=payload.full_name or "Growth Manager"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    response.set_cookie(key="user_email", value=user.email, max_age=30*86400, httponly=False, samesite="lax", path="/")
    return user

@router.post("/login", response_model=UserResponse)
def login(payload: UserLogin, response: Response, db = Depends(get_db)):
    email = payload.email.strip().lower()
    hashed = _hash_password(payload.password)

    stmt = select(User).where(User.email == email)
    res = db.execute(stmt)
    user = res.scalars().first()

    if not user:
        # Seamless Auto-Registration on first login
        full_name = email.split("@")[0].replace(".", " ").replace("_", " ").title()
        user = User(
            email=email,
            hashed_password=hashed,
            full_name=full_name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif user.hashed_password != hashed:
        user.hashed_password = hashed
        db.add(user)
        db.commit()
        db.refresh(user)

    response.set_cookie(key="user_email", value=user.email, max_age=30*86400, httponly=False, samesite="lax", path="/")
    return user

@router.get("/me", response_model=Optional[UserResponse])
def get_current_user(
    request: Request,
    user_email: Optional[str] = Cookie(None),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    db = Depends(get_db)
):
    email = user_email or x_user_email or request.query_params.get("user_email")
    if not email:
        return None

    stmt = select(User).where(User.email == email.strip().lower())
    res = db.execute(stmt)
    user = res.scalars().first()
    return user

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="user_email", path="/")
    return {"message": "Logged out successfully."}

