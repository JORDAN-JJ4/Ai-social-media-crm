import json
import datetime
from sqlalchemy import select
from backend.agents.base_agent import BaseAgent
from backend.models import TrendMemory
from backend.services.gemini_service import GeminiService

class TrendResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__("trend_agent", "Hourly Market & Trend Research Agent")

    async def execute(self, db) -> dict:
        settings = await self.get_settings(db)
        category = settings.page_category
        language = settings.language

        await self.log_action(db, "HOURLY_MARKET_SCAN", f"Scanning hourly market trends & breaking news for category '{category}' in {language}...")

        gemini = GeminiService(settings.gemini_api_key)
        prompt = f"""
        Act as an Hourly Market News & Trend Intelligence Officer for a Facebook/Instagram page in category '{category}'.
        Language: {language}.
        Current ISO Timestamp: {datetime.datetime.utcnow().isoformat()}.

        Task:
        1. Scan for recent market updates, breaking news, viral debates, or new trends in '{category}'.
        2. Identify topics that are post-worthy RIGHT NOW to grow page reach.
        3. Filter out fake news, unverified rumors, and spam.
        4. Select best format: "Carousel" | "Infographic" | "Article" | "Reel" | "Story"

        Return JSON format with key "trends":
        [
            {{
                "topic": "Title of trend or breaking news",
                "format_type": "Carousel" | "Infographic" | "Article" | "Reel" | "Story",
                "relevance_score": 0.95,
                "summary": "Key market insight, headline, or hook summary",
                "source_type": "Breaking News" | "Market Update" | "Viral Trend"
            }}
        ]
        """
        response_text = await gemini.generate_text(prompt, json_mode=True)
        new_trends_count = 0

        try:
            parsed = json.loads(response_text)
            trends_list = parsed.get("trends", [])
            
            for item in trends_list:
                topic = item.get("topic", "").strip()
                if not topic:
                    continue

                stmt = select(TrendMemory).where(TrendMemory.topic == topic)
                res = db.execute(stmt)
                existing = res.scalars().first()

                if not existing:
                    trend_obj = TrendMemory(
                        topic=topic,
                        category=category,
                        format_type=item.get("format_type", "Carousel"),
                        relevance_score=float(item.get("relevance_score", 0.9)),
                        summary=item.get("summary", ""),
                        source_type=item.get("source_type", "Market Update"),
                        is_used=False
                    )
                    db.add(trend_obj)
                    new_trends_count += 1
            
            db.commit()
            await self.log_action(db, "HOURLY_TRENDS_SAVED", f"Discovered {new_trends_count} hourly post-worthy market updates for '{category}'.", level="SUCCESS")
            return {"status": "SUCCESS", "new_trends": new_trends_count}

        except Exception as e:
            await self.log_action(db, "TREND_RESEARCH_ERROR", f"Error parsing trend data: {str(e)}", level="ERROR")
            return {"status": "ERROR", "error": str(e)}
