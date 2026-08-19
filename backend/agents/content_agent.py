import json
import datetime
from sqlalchemy import select
from backend.agents.base_agent import BaseAgent
from backend.models import ContentPost, TrendMemory, Strategy, AgentMemory
from backend.services.gemini_service import GeminiService

class ContentAgent(BaseAgent):
    def __init__(self):
        super().__init__("content_agent", "Human Growth & Content Manager Agent")

    async def execute(self, db, force: bool = False) -> dict:
        settings = await self.get_settings(db)
        
        stmt_strat = select(Strategy).order_by(Strategy.id.desc()).limit(1)
        res_strat = db.execute(stmt_strat)
        strategy = res_strat.scalars().first()
        target_count = strategy.target_posts_count if strategy else 3

        today_start = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
        stmt_today = select(ContentPost).where(ContentPost.created_at >= today_start)
        res_today = db.execute(stmt_today)
        existing_today = res_today.scalars().all()

        if len(existing_today) >= target_count and not force:
            await self.log_action(db, "CONTENT_QUOTA_REACHED", f"Target post quota ({target_count}) for today is already fulfilled.")
            return {"status": "SUCCESS", "created": 0, "reason": "QUOTA_FULL"}


        await self.log_action(db, "GENERATING_CONTENT", f"Human-like AI Manager drafting authentic post/article concept ({len(existing_today) + 1}/{target_count})...")

        stmt_trend = select(TrendMemory).where(TrendMemory.is_used == False).order_by(TrendMemory.relevance_score.desc()).limit(1)
        res_trend = db.execute(stmt_trend)
        trend = res_trend.scalars().first()
        trend_context = f"Topic: {trend.topic}. Summary: {trend.summary}" if trend else f"Category focus: {settings.page_category}"

        stmt_hist = select(ContentPost.hook, ContentPost.title, ContentPost.hashtags).order_by(ContentPost.id.desc()).limit(20)
        res_hist = db.execute(stmt_hist)
        history_rows = res_hist.all()
        used_hooks = [r[0] for r in history_rows if r[0]]
        used_titles = [r[1] for r in history_rows if r[1]]

        stmt_mem = select(AgentMemory).where(AgentMemory.memory_key == "top_performing_hooks")
        res_mem = db.execute(stmt_mem)
        mem_item = res_mem.scalars().first()
        proven_hooks = mem_item.content if mem_item else []

        page_about_text = getattr(settings, "page_about", None) or ""
        target_aud = getattr(settings, "target_audience", None) or "Targeted Audience"
        growth_obj = getattr(settings, "growth_goal", None) or "Brand Building & High Engagement"
        brand_tone = getattr(settings, "tone_of_voice", None) or "Professional, Authoritative & Engaging"
        custom_inst = getattr(settings, "custom_instructions", None) or ""

        gemini = GeminiService(settings.gemini_api_key)
        prompt = f"""
        Act as an Expert Human Growth Manager and Senior Content Director for the Facebook Page '{settings.facebook_page_id}'.
        Page Category: '{settings.page_category}'.
        Language: {settings.language}.

        CRITICAL PAGE ABOUT & BUSINESS DESCRIPTION (ANALYZE THIS TO UNDERSTAND THE EXACT BUSINESS):
        "{page_about_text if page_about_text else 'Page category: ' + settings.page_category}"

        TARGET AUDIENCE: {target_aud}.
        PRIMARY GROWTH GOAL: {growth_obj}.
        BRAND TONE OF VOICE: {brand_tone}.
        SPECIAL CUSTOM INSTRUCTIONS: {custom_inst}.


        Trend Source / Market Update: {trend_context}
        Proven Winning Hook Styles: {json.dumps(proven_hooks)}
        CRITICAL RULE: DO NOT REPEAT ANY OF THESE USED HOOKS OR TITLES:
        Used Hooks: {json.dumps(used_hooks[:10])}
        Used Titles: {json.dumps(used_titles[:10])}

        GENERATE A 100% HUMAN-LIKE HIGH IMPACT SOCIAL POST OR ARTICLE:
        - NEVER sound like a generic AI assistant. Write in an authentic human voice aligned with tone '{brand_tone}'.
        - Include an unforgettable scroll-stopping hook (1st line).
        - Create a clear headline/title.
        - Write a full caption rich in actionable value, key insights, and clear paragraph spacing.
        - Create a natural CTA tailored to growth goal '{growth_obj}'.
        - 5-8 targeted high-relevance hashtags.
        - Select Media Type: "CAROUSEL" | "IMAGE" | "REEL"
        - Select Angle: "EDUCATIONAL" | "ENTERTAINMENT" | "NEWS_UPDATE" | "BREAKING"
        - Write detailed Image Prompt for visual graphic design.

        Return JSON format:
        {{
            "title": "Headline or Article Title",
            "hook": "Scroll stopping hook text",
            "caption": "Full authentic human caption...",
            "cta": "Natural call to action",
            "hashtags": "#Tag1 #Tag2 #Tag3",
            "media_type": "CAROUSEL",
            "content_angle": "NEWS_UPDATE",
            "image_prompt": "Detailed graphic poster design prompt...",
            "video_prompt": "Short script or reel prompt..."
        }}
        """


        response_text = await gemini.generate_text(prompt, json_mode=True)
        try:
            data = json.loads(response_text)
            scheduled_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)

            post = ContentPost(
                title=data.get("title", "Untitled Growth Post"),
                hook=data.get("hook", ""),
                caption=data.get("caption", ""),
                cta=data.get("cta", ""),
                hashtags=data.get("hashtags", ""),
                media_type=data.get("media_type", "CAROUSEL"),
                content_angle=data.get("content_angle", "EDUCATIONAL"),
                image_prompt=data.get("image_prompt", ""),
                video_prompt=data.get("video_prompt", ""),
                target_platform="BOTH",
                status="DRAFT",
                scheduled_time=scheduled_time
            )
            db.add(post)

            if trend:
                trend.is_used = True
                db.add(trend)

            db.commit()
            db.refresh(post)

            await self.log_action(
                db, 
                "CONTENT_CREATED", 
                f"Generated Human-like Post/Article ID {post.id}: '{post.title}' (Format: {post.media_type})", 
                level="SUCCESS"
            )
            return {"status": "SUCCESS", "post_id": post.id, "title": post.title}

        except Exception as e:
            await self.log_action(db, "CONTENT_ERROR", f"Error generating content post: {str(e)}", level="ERROR")
            return {"status": "ERROR", "error": str(e)}
