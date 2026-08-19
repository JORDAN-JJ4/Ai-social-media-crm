from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from backend.database import get_db
from backend.models import ContentPost
from backend.schemas import PostResponse

router = APIRouter(prefix="/api/posts", tags=["Content Posts"])

@router.get("", response_model=List[PostResponse])
def list_posts(
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db = Depends(get_db)
):
    stmt = select(ContentPost)
    if status and status.upper() != "ALL":
        stmt = stmt.where(ContentPost.status == status.upper())
    stmt = stmt.order_by(ContentPost.id.desc()).limit(limit)
    
    res = db.execute(stmt)
    posts = res.scalars().all()
    return posts

@router.get("/{post_id}", response_model=PostResponse)
def get_post_detail(post_id: int, db = Depends(get_db)):
    stmt = select(ContentPost).where(ContentPost.id == post_id)
    res = db.execute(stmt)
    post = res.scalars().first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post
