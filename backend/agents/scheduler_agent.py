import json
import datetime
import random
from sqlalchemy import select
from backend.agents.base_agent import BaseAgent
from backend.models import ContentPost, AgentMemory

class SchedulerAgent(BaseAgent):
    def __init__(self):
        super().__init__("scheduler_agent", "Scheduler Agent")

    async def execute(self, db) -> dict:
        settings = await self.get_settings(db)
        
        stmt = select(ContentPost).where(ContentPost.status == "DRAFT").where(ContentPost.media_urls != None).order_by(ContentPost.id.asc())
        res = db.execute(stmt)
        pending_posts = res.scalars().all()

        if not pending_posts:
            await self.log_action(db, "SCHEDULER_IDLE", "No pending posts waiting for dynamic time assignment.")
            return {"status": "SUCCESS", "scheduled": 0}

        stmt_mem = select(AgentMemory).where(AgentMemory.memory_key == "best_posting_times")
        res_mem = db.execute(stmt_mem)
        mem_item = res_mem.scalars().first()
        best_times_memory = mem_item.content if mem_item else {"optimal_hours": [14, 18, 20], "schedule_shift_detected": False}

        optimal_hours = best_times_memory.get("optimal_hours", [14, 18, 20])
        shift_detected = best_times_memory.get("schedule_shift_detected", False)

        scheduled_count = 0
        now = datetime.datetime.utcnow()

        for post in pending_posts:
            selected_hour = random.choice(optimal_hours)
            if shift_detected:
                selected_hour = (selected_hour + 2) % 24

            target_time = now.replace(hour=selected_hour, minute=random.randint(0, 59), second=0)
            if target_time <= now:
                target_time += datetime.timedelta(days=1)

            post.scheduled_time = target_time
            post.status = "SCHEDULED"
            db.add(post)
            scheduled_count += 1

            await self.log_action(
                db, 
                "POST_SCHEDULED", 
                f"Post ID {post.id} scheduled for {target_time.strftime('%Y-%m-%d %H:%M UTC')} (Hour: {selected_hour}:00, Adaptive shift: {shift_detected})", 
                level="SUCCESS"
            )

        db.commit()
        return {"status": "SUCCESS", "scheduled": scheduled_count}
