from fastapi import Depends, HTTPException, Cookie, Header, Request
from sqlalchemy import select
from typing import Optional
import datetime
from backend.database import get_db
from backend.models import User, ConnectedPage, UserSession
from backend.config import settings

async def get_current_user(
    request: Request,
    session_id: Optional[str] = Cookie(None),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    csrf_token: Optional[str] = Cookie(None, alias="csrf_token"),
    x_csrf_token: Optional[str] = Header(None, alias="X-CSRF-Token"),
    db = Depends(get_db)
) -> User:
    # 1. X-User-Email is ONLY allowed as fallback in development mode, but takes precedence if present
    user = None
    authenticated_via_header = False

    if settings.DEBUG and x_user_email:
        stmt = select(User).where(User.email == x_user_email.strip().lower())
        user = db.execute(stmt).scalars().first()
        if user:
            authenticated_via_header = True

    # 2. Try secure session next
    if not user and session_id:
        stmt = select(UserSession).where(
            UserSession.session_token == session_id,
            UserSession.expires_at > datetime.datetime.utcnow()
        )
        session = db.execute(stmt).scalars().first()
        if session:
            stmt_u = select(User).where(User.id == session.user_id)
            user = db.execute(stmt_u).scalars().first()

    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # 3. Perform CSRF check if request is state-changing (POST, PUT, PATCH, DELETE)
    # and authenticated via cookie session_id.
    if request.method in ["POST", "PUT", "PATCH", "DELETE"] and not authenticated_via_header:
        if not csrf_token or not x_csrf_token or csrf_token != x_csrf_token:
            raise HTTPException(status_code=403, detail="CSRF token validation failed")

    return user



async def verify_page_ownership(
    facebook_page_id: str,
    user: User = Depends(get_current_user),
    db = Depends(get_db)
) -> ConnectedPage:
    stmt = select(ConnectedPage).where(ConnectedPage.facebook_page_id == facebook_page_id)
    res = db.execute(stmt)
    page = res.scalars().first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Auto-claim ownership if page currently has no owner
    if page.user_id is None:
        page.user_id = user.id
        db.add(page)
        db.commit()
        db.refresh(page)
    
    # Check if page user_id matches user.id
    if page.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this connected page")
    
    return page


