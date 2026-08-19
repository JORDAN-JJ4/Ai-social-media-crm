import os
from pydantic import BaseModel, model_validator

def _load_env_file(filepath=".env"):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    if k not in os.environ:
                        v = v.strip('"').strip("'")
                        os.environ[k] = v

_load_env_file()

class Settings(BaseModel):
    APP_NAME: str = os.getenv("APP_NAME", "Omni FB Analytics")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./social_growth.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-autonomous-key-2026")
    TOKEN_ENCRYPTION_KEY: str = os.getenv("TOKEN_ENCRYPTION_KEY", "")
    CRON_SECRET: str = os.getenv("CRON_SECRET", "")
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "False").lower() == "true"
    
    FACEBOOK_APP_ID: str = os.getenv("FACEBOOK_APP_ID", "")
    FACEBOOK_CLIENT_SECRET: str = os.getenv("FACEBOOK_CLIENT_SECRET", "")
    FACEBOOK_REDIRECT_URI: str = os.getenv("FACEBOOK_REDIRECT_URI", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Execution frequency for Autonomous Orchestrator tick in minutes
    AUTONOMOUS_CYCLE_INTERVAL_MINUTES: int = int(os.getenv("AUTONOMOUS_CYCLE_INTERVAL_MINUTES", "60"))

    @model_validator(mode="after")
    def validate_production_safeguards(self) -> "Settings":
        is_prod_env = bool(os.getenv("VERCEL")) or bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
        is_prod = not self.DEBUG or is_prod_env

        if is_prod_env and self.DEBUG:
            raise ValueError("DEBUG mode must be disabled in production environments.")

        if is_prod and self.SECRET_KEY == "super-secret-autonomous-key-2026":
            raise ValueError("Production SECRET_KEY cannot be the default key.")

        if is_prod and not self.TOKEN_ENCRYPTION_KEY:
            raise ValueError("Production TOKEN_ENCRYPTION_KEY environment variable is required.")

        if self.TOKEN_ENCRYPTION_KEY:
            try:
                from cryptography.fernet import Fernet
                Fernet(self.TOKEN_ENCRYPTION_KEY.encode())
            except Exception as e:
                raise ValueError(f"Invalid TOKEN_ENCRYPTION_KEY configuration: {e}")

        return self

settings = Settings()
