import logging
import datetime
from sqlalchemy import select
from backend.models import SystemLog, SystemSettings

class BaseAgent:
    def __init__(self, agent_name: str, display_name: str):
        self.agent_name = agent_name
        self.display_name = display_name
        self.logger = logging.getLogger(f"agent.{agent_name}")

    async def get_settings(self, db) -> SystemSettings:
        stmt = select(SystemSettings).order_by(SystemSettings.id.desc())
        res = db.execute(stmt)
        settings = res.scalars().first()
        if not settings:
            settings = SystemSettings(page_category="Technology & AI", language="English", auto_mode_enabled=False)
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings

    async def log_action(self, db, action: str, details: str, level: str = "INFO"):
        log_entry = SystemLog(
            agent_name=self.agent_name,
            level=level,
            action=action,
            details=details,
            created_at=datetime.datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()
        self.logger.info(f"[{self.display_name}] {action} - {details[:100]}")
