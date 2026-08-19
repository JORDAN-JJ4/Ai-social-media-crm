import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger("database")

# --- Determine the database URL ---
# On Vercel/Lambda: always use SQLite in /tmp (bypasses all env var parsing issues)
_is_serverless = bool(os.getenv("VERCEL")) or bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME"))

if _is_serverless:
    db_url = "sqlite:////tmp/facebook_crm.db"
    logger.info("Serverless environment: using SQLite at /tmp/facebook_crm.db")
else:
    # Local / self-hosted: read from environment
    _raw_url = os.getenv("DATABASE_URL", "").strip().strip('"').strip("'")
    if not _raw_url:
        _raw_url = "sqlite:///./social_growth.db"
    # Fix legacy postgres:// URLs for SQLAlchemy 2.x
    if _raw_url.startswith("postgres://"):
        _raw_url = _raw_url.replace("postgres://", "postgresql://", 1)
    # Fix aiosqlite URLs
    if "sqlite+aiosqlite:///" in _raw_url:
        _raw_url = _raw_url.replace("sqlite+aiosqlite:///", "sqlite:///")
    db_url = _raw_url

# --- Set SQLite connect args ---
connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}

# --- Create the engine ---
engine = create_engine(
    db_url,
    echo=False,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

_db_initialized = False

def init_db():
    global _db_initialized
    if not _db_initialized:
        if "sqlite" in db_url:
            logger.info("SQLite: auto-creating all tables.")
            try:
                Base.metadata.create_all(bind=engine)
                logger.info("SQLite tables created/verified OK.")
            except Exception as e:
                logger.error(f"Error creating SQLite tables: {e}")
                raise e
        else:
            logger.info("Non-SQLite DB: skipping auto table creation — use Alembic migrations.")
        _db_initialized = True

def get_db():
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
