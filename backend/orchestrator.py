import asyncio
import logging
import datetime
from sqlalchemy import select
from backend.database import SessionLocal
from backend.models import SystemSettings
from backend.agents.master_autonomous_agent import MasterAutonomousAgent

logger = logging.getLogger("orchestrator")

class AutonomousOrchestrator:
    """
    Orchestrator for single Master Autonomous AI Agent per Facebook Page.
    """
    def __init__(self):
        self.master_agent = MasterAutonomousAgent()
        self.is_running = False
        self.last_cycle_timestamp = None
        self.agent_statuses = {
            "master_autonomous_agent": {
                "name": "Master AI Autonomous Agent",
                "status": "IDLE",
                "last_run": None,
                "last_action": "Initialized Master AI Agent per FB Page",
                "metrics": "Ready"
            }
        }

    async def run_full_autonomous_cycle(self, force: bool = False) -> dict:
        if self.is_running and not force:
            return {"status": "BUSY", "message": "Master AI Autonomous Agent is already executing."}

        self.is_running = True
        cycle_start_time = datetime.datetime.utcnow().isoformat()
        results = {}

        try:
            db = SessionLocal()
            try:
                stmt = select(SystemSettings).order_by(SystemSettings.id.desc())
                res = db.execute(stmt)
                settings = res.scalars().first()

                if not settings or (not settings.auto_mode_enabled and not force):
                    logger.info("Autonomous mode is disabled. Skipping automatic execution cycle.")
                    self.is_running = False
                    return {"status": "SKIPPED", "reason": "AUTO_MODE_DISABLED"}

                await self._run_single_agent(db, "master_autonomous_agent", self.master_agent, results, force=force)

                self.last_cycle_timestamp = datetime.datetime.utcnow().isoformat()
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error during autonomous cycle execution: {e}")
            results["cycle_error"] = str(e)
        finally:
            self.is_running = False

        return {"status": "COMPLETED", "start_time": cycle_start_time, "end_time": self.last_cycle_timestamp, "agent_results": results}

    async def _run_single_agent(self, db, key: str, agent, results_dict: dict, force: bool = False):
        now_str = datetime.datetime.utcnow().strftime("%H:%M:%S")
        self.agent_statuses[key]["status"] = "RUNNING"
        self.agent_statuses[key]["last_run"] = now_str
        self.agent_statuses[key]["last_action"] = "Executing Master AI Autonomous task..."

        try:
            import inspect
            sig = inspect.signature(agent.execute)
            if "force" in sig.parameters:
                res = await agent.execute(db, force=force)
            else:
                res = await agent.execute(db)

            results_dict[key] = res
            self.agent_statuses[key]["status"] = "COMPLETED" if res.get("status") == "SUCCESS" else "IDLE"
            self.agent_statuses[key]["last_action"] = f"Finished successfully ({res.get('title', res.get('status'))})"
            self.agent_statuses[key]["metrics"] = str(res)
        except Exception as e:
            logger.error(f"Agent {key} error: {e}")
            results_dict[key] = {"status": "ERROR", "error": str(e)}
            self.agent_statuses[key]["status"] = "ERROR"
            self.agent_statuses[key]["last_action"] = f"Error: {str(e)[:80]}"

    def get_agent_status_list(self) -> list:
        output = []
        for k, v in self.agent_statuses.items():
            output.append({
                "agent_name": k,
                "display_name": v["name"],
                "status": v["status"],
                "last_run": v["last_run"],
                "last_action": v["last_action"],
                "metrics_summary": v["metrics"]
            })
        return output

orchestrator = AutonomousOrchestrator()
