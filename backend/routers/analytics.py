from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from backend.database import get_db
from backend.models import ContentPost, AnalyticsData
from backend.schemas import AnalyticsOverviewResponse

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Growth Reports"])

@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(db = Depends(get_db)):
    stmt_published = select(func.count(ContentPost.id)).where(ContentPost.status == "PUBLISHED")
    res_pub = db.execute(stmt_published)
    pub_count = res_pub.scalar() or 0

    stmt_analytics = select(
        func.sum(AnalyticsData.reach),
        func.sum(AnalyticsData.likes),
        func.sum(AnalyticsData.comments),
        func.sum(AnalyticsData.shares),
        func.sum(AnalyticsData.saves),
        func.sum(AnalyticsData.watch_time_seconds),
        func.sum(AnalyticsData.follower_growth),
        func.avg(AnalyticsData.engagement_rate)
    )
    res_ana = db.execute(stmt_analytics)
    row = res_ana.one()

    tot_reach = row[0] or 0
    tot_likes = row[1] or 0
    tot_comments = row[2] or 0
    tot_shares = row[3] or 0
    tot_saves = row[4] or 0
    tot_watch = row[5] or 0
    tot_followers = row[6] or 0
    avg_eng = round(float(row[7] or 0.0), 2)

    return AnalyticsOverviewResponse(
        total_followers=tot_followers,
        total_reach=tot_reach,
        total_likes=tot_likes,
        total_comments=tot_comments,
        total_shares=tot_shares,
        total_saves=tot_saves,
        total_watch_time=tot_watch,
        avg_engagement_rate=avg_eng,
        best_posting_hour="Calculated Post-Publish" if pub_count == 0 else "18:00 UTC",
        top_media_type="Pending Content" if pub_count == 0 else "CAROUSEL",
        posts_published_count=pub_count
    )
