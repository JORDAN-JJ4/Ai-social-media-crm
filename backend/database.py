import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import settings

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

import logging

logger = logging.getLogger("database")

_db_initialized = False
fallback_engine = None
fallback_SessionLocal = None

def init_db():
    global _db_initialized, engine, SessionLocal, fallback_engine, fallback_SessionLocal
    if not _db_initialized:
        try:
            Base.metadata.create_all(bind=engine)
            _db_initialized = True
        except Exception as e:
            logger.error(f"PostgreSQL connection failed ({e}). Falling back to local /tmp database...")
            try:
                tmp_url = "sqlite:////tmp/facebook_crm.db"
                fallback_engine = create_engine(tmp_url, connect_args={"check_same_thread": False}, pool_pre_ping=True)
                fallback_SessionLocal = sessionmaker(bind=fallback_engine, autocommit=False, autoflush=False)
                Base.metadata.create_all(bind=fallback_engine)
                engine = fallback_engine
                SessionLocal = fallback_SessionLocal
                _db_initialized = True
            except Exception as ex:
                logger.error(f"Fallback SQLite database failed: {ex}")

def get_db():
    global SessionLocal
    init_db()
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        logger.error(f"Database session error ({e}). Trying fallback database...")
        tmp_url = "sqlite:////tmp/facebook_crm.db"
        fb_eng = create_engine(tmp_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=fb_eng)
        fb_sess = sessionmaker(bind=fb_eng, autocommit=False, autoflush=False)()
        try:
            yield fb_sess
        finally:
            fb_sess.close()
    finally:
        try:
            db.close()
        except:
            pass


