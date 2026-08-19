import json
import datetime
from sqlalchemy import select
from backend.agents.base_agent import BaseAgent
from backend.models import ContentPost, AnalyticsData, AgentMemory
from backend.services.gemini_service import GeminiService

class LearningAgent(BaseAgent):
    def __init__(self):
        super().__init__("learning_agent", "Learning Agent")

    async def execute(self, db) -> dict:
        settings = await self.get_settings(db)
        
        stmt = select(ContentPost, AnalyticsData).join(AnalyticsData, ContentPost.id == AnalyticsData.post_id).order_by(AnalyticsData.engagement_rate.desc()).limit(10)
        res = db.execute(stmt)
        rows = res.all()

        if not rows:
            await self.log_action(db, "LEARNING_IDLE", "Insufficient performance data to run AI self-learning cycle.")
            return {"status": "SUCCESS", "insights_generated": 0}

        performance_summary = []
        for post, analytics in rows:
            performance_summary.append({
                "id": post.id,
                "title": post.title,
                "hook": post.hook,
                "media_type": post.media_type,
                "angle": post.content_angle,
                "reach": analytics.reach,
                "engagement_rate": analytics.engagement_rate,
                "saves": analytics.saves,
                "shares": analytics.shares
            })

        await self.log_action(db, "ANALYZING_PATTERNS", f"Running AI deep-learning engine across top {len(rows)} post performances...")

        gemini = GeminiService(settings.gemini_api_key)
        prompt = f"""
        Act as an AI Machine Learning Growth Analyst for social media.
        Category: {settings.page_category}
        Performance Data Summary: {json.dumps(performance_summary)}

        Answer these questions & derive core rules:
        1. What worked?
        2. What failed?
        3. Which hooks attracted maximum attention?
        4. Which topics/angles generated more shares/saves?
        5. Should we shift posting times or media ratios?

        Return JSON format:
        {{
            "what_worked": "Carousels with mystery hooks achieved 6.8% engagement...",
            "what_failed": "Static promotional posts had low share counts...",
            "top_performing_hooks": ["Hook phrase 1", "Hook phrase 2"],
            "best_posting_times": {{
                "optimal_hours": [18, 20, 21],
                "schedule_shift_detected": false
            }},
            "strategy_insights": {{
                "recommended_media_type": "CAROUSEL",
                "recommended_angle": "EDUCATIONAL",
                "content_frequency_boost": true
            }}
        }}
        """

        response_text = await gemini.generate_text(prompt, json_mode=True)
        try:
            data = json.loads(response_text)

            memories_to_update = [
                ("learning_summary", {
                    "what_worked": data.get("what_worked"),
                    "what_failed": data.get("what_failed"),
                    "last_updated": datetime.datetime.utcnow().isoformat()
                }),
                ("top_performing_hooks", data.get("top_performing_hooks", [])),
                ("best_posting_times", data.get("best_posting_times", {"optimal_hours": [14, 18, 20]})),
                ("strategy_insights", data.get("strategy_insights", {}))
            ]

            for key, val in memories_to_update:
                stmt_mem = select(AgentMemory).where(AgentMemory.memory_key == key)
                res_mem = db.execute(stmt_mem)
                existing_mem = res_mem.scalars().first()

                if existing_mem:
                    existing_mem.content = val
                    existing_mem.updated_at = datetime.datetime.utcnow()
                    db.add(existing_mem)
                else:
                    new_mem = AgentMemory(
                        memory_key=key,
                        category=settings.page_category,
                        content=val
                    )
                    db.add(new_mem)

            db.commit()
            await self.log_action(
                db, 
                "LEARNING_CYCLE_COMPLETE", 
                f"Updated AI Memory Matrix. Insight: {data.get('what_worked', 'Learned new performance rules')[:120]}...", 
                level="SUCCESS"
            )
            return {"status": "SUCCESS", "insights_generated": len(memories_to_update)}

        except Exception as e:
            await self.log_action(db, "LEARNING_ERROR", f"Error during learning cycle: {str(e)}", level="ERROR")
            return {"status": "ERROR", "error": str(e)}
