import json
import datetime
from sqlalchemy import select
from backend.agents.base_agent import BaseAgent
from backend.models import Strategy, AgentMemory
from backend.services.gemini_service import GeminiService

class StrategyAgent(BaseAgent):
    def __init__(self):
        super().__init__("strategy_agent", "Strategy Agent")

    async def execute(self, db) -> dict:
        settings = await self.get_settings(db)
        today_str = datetime.date.today().isoformat()

        await self.log_action(db, "FORMULATING_STRATEGY", f"Calculating content strategy matrix for {today_str}...")

        stmt_prev = select(Strategy).order_by(Strategy.id.desc()).limit(3)
        res_prev = db.execute(stmt_prev)
        prev_strategies = res_prev.scalars().all()
        prev_summary = [f"{s.target_date}: {s.focus_summary}" for s in prev_strategies]

        stmt_mem = select(AgentMemory).where(AgentMemory.memory_key == "strategy_insights")
        res_mem = db.execute(stmt_mem)
        memory_item = res_mem.scalars().first()
        learned_rules = memory_item.content if memory_item else {}

        gemini = GeminiService(settings.gemini_api_key)
        prompt = f"""
        Act as a Master Social Media Content Strategist for category '{settings.page_category}'.
        Date: {today_str}.
        Learned Performance Rules: {json.dumps(learned_rules)}
        Previous Strategies (Do not repeat exact setup): {json.dumps(prev_summary)}

        Decide today's strategy:
        - Number of posts today (1 to 3)
        - Image vs Reel vs Carousel ratio (sum to 1.0)
        - Educational % vs Entertainment % vs Promotional % (sum to 100)
        - Core Strategic Focus

        Return JSON format:
        {{
            "target_posts_count": 2,
            "image_ratio": 0.3,
            "reel_ratio": 0.5,
            "carousel_ratio": 0.2,
            "educational_pct": 50,
            "entertainment_pct": 30,
            "promotional_pct": 20,
            "focus_summary": "High-retention reel hooks paired with interactive carousels to maximize shares and saves."
        }}
        """

        response_text = await gemini.generate_text(prompt, json_mode=True)
        try:
            data = json.loads(response_text)
            
            strat = Strategy(
                target_date=today_str,
                target_posts_count=int(data.get("target_posts_count", 2)),
                image_ratio=float(data.get("image_ratio", 0.33)),
                reel_ratio=float(data.get("reel_ratio", 0.33)),
                carousel_ratio=float(data.get("carousel_ratio", 0.34)),
                educational_pct=int(data.get("educational_pct", 40)),
                entertainment_pct=int(data.get("entertainment_pct", 40)),
                promotional_pct=int(data.get("promotional_pct", 20)),
                focus_summary=data.get("focus_summary", "Balanced daily strategy.")
            )
            db.add(strat)
            db.commit()
            db.refresh(strat)

            await self.log_action(
                db, 
                "STRATEGY_UPDATED", 
                f"Planned {strat.target_posts_count} posts today. Focus: {strat.focus_summary}", 
                level="SUCCESS"
            )
            return {"status": "SUCCESS", "strategy_id": strat.id, "target_posts": strat.target_posts_count}

        except Exception as e:
            await self.log_action(db, "STRATEGY_ERROR", f"Error generating strategy: {str(e)}", level="ERROR")
            return {"status": "ERROR", "error": str(e)}
