import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import settings

logger = logging.getLogger("database")

db_url = settings.DATABASE_URL
# Guard against DATABASE_URL set to empty string in env (os.getenv returns "" not the default)
if not db_url or not db_url.strip():
    logger.warning("DATABASE_URL is empty — falling back to default SQLite database.")
    db_url = "sqlite:///./social_growth.db"
if db_url.startswith("postgres://"):
    # Fix for SQLAlchemy 1.4+ compatibility with Supabase/Heroku postgres URLs
    db_url = db_url.replace("postgres://", "postgresql://", 1)

connect_args = {}
if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    if "sqlite" in db_url and not db_url.startswith("sqlite:////tmp"):
        db_url = "sqlite:////tmp/facebook_crm.db"

if "sqlite" in db_url:
    db_url = db_url.replace("sqlite+aiosqlite:///", "sqlite:///")
    connect_args = {"check_same_thread": False}

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
            # Always auto-create SQLite tables (SQLite is ephemeral on Vercel /tmp anyway)
            logger.info("SQLite database: automatically ensuring all tables exist.")
            try:
                Base.metadata.create_all(bind=engine)
                logger.info("SQLite tables created/verified successfully.")
            except Exception as e:
                logger.error(f"Error creating SQLite tables: {e}")
                raise e
        else:
            # For PostgreSQL / real production DBs, rely on Alembic migrations
            logger.info("Non-SQLite database detected: skipping auto table creation. Use Alembic migrations.")
        _db_initialized = True

def get_db():
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
