import os
from pydantic import BaseModel

def _load_env_file(filepath=".env"):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    v = v.strip('"').strip("'")
                    os.environ[k.strip()] = v

_load_env_file()

class Settings(BaseModel):
    APP_NAME: str = os.getenv("APP_NAME", "Omni FB Analytics")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./social_growth.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-autonomous-key-2026")
    
    FACEBOOK_APP_ID: str = os.getenv("FACEBOOK_APP_ID", "")
    FACEBOOK_CLIENT_SECRET: str = os.getenv("FACEBOOK_CLIENT_SECRET", "")
    FACEBOOK_REDIRECT_URI: str = os.getenv("FACEBOOK_REDIRECT_URI", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Execution frequency for Autonomous Orchestrator tick in minutes
    AUTONOMOUS_CYCLE_INTERVAL_MINUTES: int = int(os.getenv("AUTONOMOUS_CYCLE_INTERVAL_MINUTES", "60"))

settings = Settings()
