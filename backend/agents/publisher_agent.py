import json
import datetime
from sqlalchemy import select
from backend.agents.base_agent import BaseAgent
from backend.models import ContentPost, PublishingLog
from backend.services.meta_graph_service import MetaGraphService

class PublisherAgent(BaseAgent):
    def __init__(self):
        super().__init__("publisher_agent", "Publisher Agent")

    async def execute(self, db) -> dict:
        settings = await self.get_settings(db)
        now = datetime.datetime.utcnow()

        stmt = select(ContentPost).where(
            ContentPost.status.in_(["SCHEDULED", "FAILED_RETRY"])
        ).where(ContentPost.scheduled_time <= now).order_by(ContentPost.scheduled_time.asc()).limit(3)
        
        res = db.execute(stmt)
        due_posts = res.scalars().all()

        if not due_posts:
            stmt_next = select(ContentPost).where(ContentPost.status == "SCHEDULED").order_by(ContentPost.scheduled_time.asc()).limit(1)
            res_next = db.execute(stmt_next)
            next_post = res_next.scalars().first()
            if next_post and settings.auto_mode_enabled:
                due_posts = [next_post]

        if not due_posts:
            await self.log_action(db, "PUBLISHER_IDLE", "No due scheduled posts ready for release at this time.")
            return {"status": "SUCCESS", "published": 0}

        meta_service = MetaGraphService(
            fb_page_id=settings.facebook_page_id,
            fb_access_token=settings.facebook_access_token,
            ig_account_id=settings.instagram_account_id,
            ig_access_token=settings.instagram_access_token
        )

        published_count = 0

        for post in due_posts:
            post.status = "PUBLISHING"
            db.commit()

            full_caption = f"{post.hook}\n\n{post.caption}\n\n{post.cta}\n\n{post.hashtags}"
            first_media_url = post.media_urls[0] if post.media_urls else None

            fb_res = await meta_service.publish_facebook_post(caption=full_caption, image_url=first_media_url)
            fb_log = PublishingLog(
                post_id=post.id,
                platform="FACEBOOK",
                status="SUCCESS" if fb_res.get("success") else "FAILED",
                message=f"FB Publish result: {fb_res.get('post_id') or fb_res.get('error')}",
                response_data=fb_res
            )
            db.add(fb_log)

            ig_res = await meta_service.publish_instagram_media(caption=full_caption, image_url=first_media_url or "", media_type=post.media_type)
            ig_log = PublishingLog(
                post_id=post.id,
                platform="INSTAGRAM",
                status="SUCCESS" if ig_res.get("success") else "FAILED",
                message=f"IG Publish result: {ig_res.get('post_id') or ig_res.get('error')}",
                response_data=ig_res
            )
            db.add(ig_log)

            if fb_res.get("success") or ig_res.get("success"):
                post.status = "PUBLISHED"
                post.published_time = datetime.datetime.utcnow()
                post.meta_facebook_post_id = fb_res.get("post_id")
                post.meta_instagram_post_id = ig_res.get("post_id")
                published_count += 1

                await self.log_action(
                    db, 
                    "PUBLISHED_SUCCESS", 
                    f"Successfully published post ID {post.id} to Meta platforms. (FB ID: {post.meta_facebook_post_id}, IG ID: {post.meta_instagram_post_id})", 
                    level="SUCCESS"
                )
            else:
                post.status = "FAILED_RETRY"
                await self.log_action(
                    db, 
                    "PUBLISH_FAILED", 
                    f"Failed publishing post ID {post.id}. Queued for retry.", 
                    level="ERROR"
                )

            db.add(post)

        db.commit()
        return {"status": "SUCCESS", "published": published_count}
