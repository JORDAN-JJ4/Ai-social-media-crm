import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import settings
from backend.database import init_db
from backend.orchestrator import orchestrator
from backend.routers import setup, posts, analytics, agents, logs, auth

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("main")

background_loop_task = None

async def autonomous_background_loop():
    logger.info("Autonomous AI Agent Background Scheduler Loop active.")
    while True:
        try:
            await asyncio.sleep(settings.AUTONOMOUS_CYCLE_INTERVAL_MINUTES * 60)
            logger.info("Running periodic Autonomous AI Agent cycle...")
            await orchestrator.run_full_autonomous_cycle(force=False)
        except asyncio.CancelledError:
            logger.info("Autonomous background loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in autonomous background loop: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global background_loop_task
    logger.info("Initializing Autonomous AI Social Media Growth Platform...")
    try:
        init_db()
    except Exception as e:
        logger.error(f"Error during init_db on startup: {e}")

    if not os.getenv("VERCEL") and not os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        asyncio.create_task(orchestrator.run_full_autonomous_cycle(force=True))
        background_loop_task = asyncio.create_task(autonomous_background_loop())

    yield

    if background_loop_task:
        background_loop_task.cancel()
    logger.info("Shutting down platform.")

app = FastAPI(
    title=settings.APP_NAME,
    description="Autonomous Multi-Agent AI Platform for Facebook & Instagram Growth",
    version="1.0.0",
    lifespan=lifespan
)

@app.middleware("http")
async def add_no_cache_header(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path in ["/pages", "/dashboard", "/posts", "/analytics", "/settings"]:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# Register API Routers
app.include_router(auth.router)
app.include_router(setup.router)
app.include_router(posts.router)
app.include_router(analytics.router)
app.include_router(agents.router)
app.include_router(logs.router)

# Mount Frontend static files
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_dir = os.path.join(base_dir, "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
@app.get("/landing")
async def serve_landing():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Landing page not found"}

@app.get("/onboarding")
async def serve_onboarding():
    path = os.path.join(frontend_dir, "onboarding.html")
    if os.path.exists(path):
        return FileResponse(path)
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/dashboard")
@app.get("/overview")
async def serve_dashboard():
    path = os.path.join(frontend_dir, "dashboard.html")
    if os.path.exists(path):
        return FileResponse(path)
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/posts")
async def serve_posts():
    path = os.path.join(frontend_dir, "posts.html")
    if os.path.exists(path):
        return FileResponse(path)
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/analytics")
async def serve_analytics():
    path = os.path.join(frontend_dir, "analytics.html")
    if os.path.exists(path):
        return FileResponse(path)
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/pages")
async def serve_pages():
    path = os.path.join(frontend_dir, "pages.html")
    if os.path.exists(path):
        return FileResponse(path)
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/settings")
async def serve_settings():
    path = os.path.join(frontend_dir, "settings.html")
    if os.path.exists(path):
        return FileResponse(path)
    return FileResponse(os.path.join(frontend_dir, "index.html"))


