import json
import datetime
import logging
from sqlalchemy import select
from backend.agents.base_agent import BaseAgent
from backend.models import ContentPost, PublishingLog, AgentMemory
from backend.config import settings as app_settings
from backend.services.groq_service import GroqService
from backend.services.image_service import ImageService
from backend.services.meta_graph_service import MetaGraphService

logger = logging.getLogger("master_autonomous_agent")

class MasterAutonomousAgent(BaseAgent):
    """
    Single Master AI Autonomous Agent per Facebook Page.
    Handles complete end-to-end autonomous cycle:
    Trend Research -> Growth Strategy -> Content Copywriting -> Visual Graphic Design -> Auto Publishing to Meta.
    """
    def __init__(self):
        super().__init__("master_autonomous_agent", "Master AI Autonomous Agent")

    async def execute(self, db, force: bool = False) -> dict:
        settings = await self.get_settings(db)
        
        page_name = settings.facebook_page_id or "Primary Connected Page"
        page_about = getattr(settings, "page_about", "") or "General Business & Social Growth Page"
        target_aud = getattr(settings, "target_audience", "") or "Targeted Loyal Audience"
        growth_obj = getattr(settings, "growth_goal", "") or "Brand Awareness & High Engagement"
        brand_tone = getattr(settings, "tone_of_voice", "") or "Professional, Authoritative & Engaging"
        custom_inst = getattr(settings, "custom_instructions", "") or ""
        lang = getattr(settings, "language", "English")

        await self.log_action(
            db, 
            "MASTER_AGENT_START", 
            f"Master AI Agent analyzing Page '{page_name}' Business Description: '{page_about[:60]}...'"
        )

        groq = GroqService(api_key=settings.virtux_api_key or None)

        master_prompt = f"""
        Act as the Single Master AI Autonomous Social Media Growth Agent for Facebook Page '{page_name}'.
        
        CRITICAL BUSINESS & PAGE ABOUT DESCRIPTION (ANALYZE THIS FIRST TO UNDERSTAND THE EXACT BUSINESS & PRODUCTS):
        "{page_about}"

        TARGET AUDIENCE: {target_aud}.
        PRIMARY GROWTH OBJECTIVE: {growth_obj}.
        BRAND TONE OF VOICE: {brand_tone}.
        LANGUAGE: {lang}.
        CUSTOM SPECIAL INSTRUCTIONS: {custom_inst}.

        YOUR MASTER TASK:
        Perform trend research, strategy positioning, and generate a 100% human-like high impact social media post with graphic image prompt.
        - NEVER sound like a generic AI assistant. Write in an authentic human voice matching tone '{brand_tone}'.
        - Include an unforgettable scroll-stopping hook (1st line).
        - Create a clear headline/title.
        - Write a full caption rich in actionable value, key insights, and paragraph spacing.
        - Create a natural call-to-action (CTA) for goal '{growth_obj}'.
        - 5-8 targeted high-relevance hashtags.
        - Select Media Type: "IMAGE" | "CAROUSEL" | "REEL"
        - Write a detailed Image Prompt for visual graphic poster creation.

        Return JSON format:
        {{
            "trend_analysis": "Key trend or viral topic analyzed",
            "strategy_focus": "Strategic angle for today's content",
            "title": "Headline or Article Title",
            "hook": "Scroll stopping hook line",
            "caption": "Full authentic human caption...",
            "cta": "Natural call to action",
            "hashtags": "#Tag1 #Tag2 #Tag3",
            "media_type": "IMAGE",
            "content_angle": "EDUCATIONAL",
            "image_prompt": "Detailed graphic poster design prompt..."
        }}
        """

        raw_response = await groq.generate_completion(master_prompt, json_mode=True)
        try:
            data = json.loads(raw_response)
        except Exception as e:
            logger.error(f"Error parsing Groq response JSON: {e}")
            data = json.loads(groq._generate_fallback(master_prompt, json_mode=True))

        title = data.get("title", f"Growth Insights for {page_name}")
        hook = data.get("hook", "Unlock key insights for your brand")
        caption = data.get("caption", "Discover new strategies to scale your presence online.")
        cta = data.get("cta", "Follow for more daily value!")
        hashtags = data.get("hashtags", "#Growth #SocialMedia #AI")
        media_type = data.get("media_type", "IMAGE")
        image_prompt = data.get("image_prompt", f"High quality poster graphic for: {title}")

        # Step 2: Generate Visual Image Asset / AI Video Reel Asset via Groq AI Engine
        await self.log_action(db, "MASTER_DESIGNING_VISUAL", f"Master AI Agent generating Groq AI visual asset for ({media_type}): '{title}'...")
        image_service = ImageService(virtux_api_key=settings.virtux_api_key, groq_api_key=app_settings.GROQ_API_KEY)
        
        video_prompt = data.get("video_prompt", image_prompt)
        if media_type in ["REEL", "VIDEO"]:
            video_data = await image_service.generate_video_reel(video_prompt)
            media_url = video_data.get("video_url", "")
            caption += f"\n\n🎬 AI Reel Script:\n{video_data.get('video_script', '')[:200]}..."
        else:
            media_url = await image_service.generate_image(image_prompt, media_type=media_type)


        scheduled_time = datetime.datetime.utcnow()
        post = ContentPost(
            title=title,
            hook=hook,
            caption=caption,
            cta=cta,
            hashtags=hashtags,
            media_type=media_type,
            content_angle=data.get("content_angle", "EDUCATIONAL"),
            image_prompt=image_prompt,
            media_urls=[media_url],
            target_platform="BOTH",
            status="PUBLISHING",
            scheduled_time=scheduled_time
        )
        db.add(post)
        db.commit()
        db.refresh(post)

        # Step 3: Auto-Publish Visual Photo Post to Meta Graph API (Facebook Page & Instagram)
        await self.log_action(db, "MASTER_PUBLISHING", f"Master AI Agent publishing photo post ID {post.id} to Meta Graph API...")
        full_caption = f"{post.hook}\n\n{post.caption}\n\n{post.cta}\n\n{post.hashtags}"

        meta_service = MetaGraphService(
            fb_page_id=settings.facebook_page_id,
            fb_access_token=settings.facebook_access_token,
            ig_account_id=settings.instagram_account_id,
            ig_access_token=settings.instagram_access_token
        )

        fb_res = await meta_service.publish_facebook_post(caption=full_caption, image_url=media_url)
        post.status = "PUBLISHED" if fb_res.get("success") else "SCHEDULED"
        post.published_time = datetime.datetime.utcnow() if fb_res.get("success") else None
        db.add(post)

        fb_log = PublishingLog(
            post_id=post.id,
            platform="FACEBOOK",
            status="SUCCESS" if fb_res.get("success") else "FAILED",
            message=f"Master Agent Publish Result: {fb_res.get('post_id') or fb_res.get('error')}",
            response_data=fb_res
        )
        db.add(fb_log)
        db.commit()

        await self.log_action(
            db, 
            "MASTER_AGENT_COMPLETE", 
            f"Master AI Agent completed full cycle for '{page_name}'. Published Post ID {post.id}: '{title}'!",
            level="SUCCESS"
        )

        return {
            "status": "SUCCESS",
            "post_id": post.id,
            "title": title,
            "media_url": media_url,
            "fb_result": fb_res
        }
