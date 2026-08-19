import json
import datetime
from sqlalchemy import select
from backend.agents.base_agent import BaseAgent
from backend.models import ContentPost, AnalyticsData
from backend.services.meta_graph_service import MetaGraphService

class AnalyticsAgent(BaseAgent):
    def __init__(self):
        super().__init__("analytics_agent", "Analytics Agent")

    async def execute(self, db) -> dict:
        settings = await self.get_settings(db)
        
        stmt = select(ContentPost).where(ContentPost.status == "PUBLISHED").order_by(ContentPost.published_time.desc()).limit(10)
        res = db.execute(stmt)
        published_posts = res.scalars().all()

        if not published_posts:
            await self.log_action(db, "ANALYTICS_IDLE", "No published posts available to analyze metrics.")
            return {"status": "SUCCESS", "analyzed": 0}

        meta_service = MetaGraphService(
            fb_page_id=settings.facebook_page_id,
            fb_access_token=settings.facebook_access_token,
            ig_account_id=settings.instagram_account_id,
            ig_access_token=settings.instagram_access_token
        )

        analyzed_count = 0
        total_reach = 0

        for post in published_posts:
            metrics = await meta_service.fetch_post_analytics(post.meta_facebook_post_id or post.meta_instagram_post_id or "demo")
            
            analytics_entry = AnalyticsData(
                post_id=post.id,
                platform=post.target_platform,
                reach=metrics.get("reach", 0),
                impressions=metrics.get("impressions", 0),
                likes=metrics.get("likes", 0),
                comments=metrics.get("comments", 0),
                shares=metrics.get("shares", 0),
                saves=metrics.get("saves", 0),
                watch_time_seconds=metrics.get("watch_time_seconds", 0),
                follower_growth=metrics.get("follower_growth", 0),
                engagement_rate=metrics.get("engagement_rate", 0.0)
            )
            db.add(analytics_entry)
            analyzed_count += 1
            total_reach += metrics.get("reach", 0)

        db.commit()
        await self.log_action(
            db, 
            "ANALYTICS_COLLECTED", 
            f"Analyzed {analyzed_count} published posts. Combined Reach: {total_reach:,} impressions.", 
            level="SUCCESS"
        )
        return {"status": "SUCCESS", "analyzed": analyzed_count, "total_reach": total_reach}
