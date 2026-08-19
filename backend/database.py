import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import settings

logger = logging.getLogger("database")

db_url = settings.DATABASE_URL
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
        if "sqlite" in db_url and settings.DEBUG:
            logger.info("SQLite development mode: automatically ensuring database tables exist.")
            try:
                Base.metadata.create_all(bind=engine)
            except Exception as e:
                logger.error(f"Error automatically creating SQLite tables: {e}")
                raise e
        else:
            logger.info("Production mode or non-SQLite database: Skipping automatic table creation. Use migrations.")
        _db_initialized = True

def get_db():
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
