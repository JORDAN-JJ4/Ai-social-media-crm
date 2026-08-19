from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from backend.database import get_db
from backend.models import SystemLog, PublishingLog
from backend.schemas import SystemLogResponse

router = APIRouter(prefix="/api/logs", tags=["Audit & Publishing Logs"])

@router.get("/system", response_model=List[SystemLogResponse])
def get_system_logs(
    limit: int = Query(50, ge=1, le=200),
    db = Depends(get_db)
):
    stmt = select(SystemLog).order_by(SystemLog.id.desc()).limit(limit)
    res = db.execute(stmt)
    return res.scalars().all()

@router.get("/publishing")
def get_publishing_logs(
    limit: int = Query(20, ge=1, le=100),
    db = Depends(get_db)
):
    stmt = select(PublishingLog).order_by(PublishingLog.id.desc()).limit(limit)
    res = db.execute(stmt)
    logs = res.scalars().all()
    return [
        {
            "id": l.id,
            "post_id": l.post_id,
            "platform": l.platform,
            "status": l.status,
            "attempt": l.attempt_count,
            "message": l.message,
            "timestamp": l.timestamp.isoformat() if l.timestamp else ""
        } for l in logs
    ]
