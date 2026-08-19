import hashlib
import datetime
import bcrypt
import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, Header, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, delete
from backend.database import get_db
from backend.models import User, UserSession
from backend.config import settings


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

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    pwd_bytes = password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False

def _legacy_hash_password(password: str) -> str:
    salt = "synapse_growth_salt_2026"
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

def is_bcrypt_hash(hashed_password: str) -> bool:
    return hashed_password.startswith("$2")

def create_user_session(db, user_id: int) -> str:
    token = secrets.token_hex(32)
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=30)
    session = UserSession(
        user_id=user_id,
        session_token=token,
        expires_at=expires_at
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return token

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

    hashed = hash_password(payload.password)
    user = User(
        email=email,
        hashed_password=hashed,
        full_name=payload.full_name or "Growth Manager"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Establish secure session
    session_token = create_user_session(db, user.id)
    response.set_cookie(
        key="session_id",
        value=session_token,
        max_age=30*86400,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        path="/"
    )
    csrf_token = secrets.token_hex(32)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        max_age=30*86400,
        httponly=False,
        secure=not settings.DEBUG,
        samesite="lax",
        path="/"
    )
    response.delete_cookie(key="user_email", path="/")
    return user

@router.post("/login", response_model=UserResponse)
def login(payload: UserLogin, response: Response, db = Depends(get_db)):
    email = payload.email.strip().lower()

    stmt = select(User).where(User.email == email)
    res = db.execute(stmt)
    user = res.scalars().first()

    if not user:
        # Seamless Auto-Registration on first login
        hashed = hash_password(payload.password)
        full_name = email.split("@")[0].replace(".", " ").replace("_", " ").title()
        user = User(
            email=email,
            hashed_password=hashed,
            full_name=full_name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # User exists, verify password
        if is_bcrypt_hash(user.hashed_password):
            if not verify_password(payload.password, user.hashed_password):
                raise HTTPException(status_code=400, detail="Invalid email or password.")
        else:
            # Legacy validation check
            legacy_hash = _legacy_hash_password(payload.password)
            if legacy_hash != user.hashed_password:
                raise HTTPException(status_code=400, detail="Invalid email or password.")

            # Migrate to bcrypt
            user.hashed_password = hash_password(payload.password)
            db.add(user)
            db.commit()
            db.refresh(user)

    # Establish secure session
    session_token = create_user_session(db, user.id)
    response.set_cookie(
        key="session_id",
        value=session_token,
        max_age=30*86400,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        path="/"
    )
    csrf_token = secrets.token_hex(32)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        max_age=30*86400,
        httponly=False,
        secure=not settings.DEBUG,
        samesite="lax",
        path="/"
    )
    response.delete_cookie(key="user_email", path="/")
    return user

@router.get("/me", response_model=Optional[UserResponse])
def get_current_user_endpoint(
    request: Request,
    session_id: Optional[str] = Cookie(None),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    db = Depends(get_db)
):
    # 1. X-User-Email fallback only in development mode, taking precedence if present
    if settings.DEBUG and x_user_email:
        stmt = select(User).where(User.email == x_user_email.strip().lower())
        user = db.execute(stmt).scalars().first()
        if user:
            return user

    # 2. Try secure session next
    if session_id:
        stmt = select(UserSession).where(
            UserSession.session_token == session_id,
            UserSession.expires_at > datetime.datetime.utcnow()
        )
        session = db.execute(stmt).scalars().first()
        if session:
            stmt_u = select(User).where(User.id == session.user_id)
            user = db.execute(stmt_u).scalars().first()
            if user:
                return user

    return None

@router.post("/logout")
def logout(request: Request, response: Response, db = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    if session_id:
        stmt = delete(UserSession).where(UserSession.session_token == session_id)
        db.execute(stmt)
        db.commit()

    response.delete_cookie(key="session_id", path="/")
    response.delete_cookie(key="csrf_token", path="/")
    response.delete_cookie(key="user_email", path="/")
    return {"message": "Logged out successfully."}
