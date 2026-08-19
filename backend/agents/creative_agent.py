import json
from sqlalchemy import select
from backend.agents.base_agent import BaseAgent
from backend.models import ContentPost
from backend.services.image_service import ImageService

class CreativeAgent(BaseAgent):
    def __init__(self):
        super().__init__("creative_agent", "Creative Agent")

    async def execute(self, db) -> dict:
        settings = await self.get_settings(db)
        
        stmt = select(ContentPost).where(ContentPost.status == "DRAFT").order_by(ContentPost.id.asc()).limit(3)
        res = db.execute(stmt)
        draft_posts = res.scalars().all()

        if not draft_posts:
            await self.log_action(db, "CREATIVE_IDLE", "No pending draft posts waiting for media generation.")
            return {"status": "SUCCESS", "processed": 0}

        image_service = ImageService(settings.virtux_api_key)
        processed_count = 0

        for post in draft_posts:
            await self.log_action(db, "GENERATING_MEDIA", f"Designing visual asset for post ID {post.id} ({post.media_type})...")
            
            prompt_to_use = post.image_prompt or f"Modern dark aesthetic creative design for: {post.title}"
            media_urls = []

            if post.media_type == "CAROUSEL":
                for i in range(1, 4):
                    slide_prompt = f"{prompt_to_use} - Slide {i} infographic visual presentation"
                    url = await image_service.generate_image(slide_prompt, media_type="IMAGE")
                    media_urls.append(url)
            else:
                url = await image_service.generate_image(prompt_to_use, media_type=post.media_type)
                media_urls.append(url)

            post.media_urls = media_urls
            db.add(post)
            processed_count += 1

            await self.log_action(
                db, 
                "MEDIA_GENERATED", 
                f"Generated {len(media_urls)} visual asset(s) for post ID {post.id}.", 
                level="SUCCESS"
            )

        db.commit()
        return {"status": "SUCCESS", "processed": processed_count}
