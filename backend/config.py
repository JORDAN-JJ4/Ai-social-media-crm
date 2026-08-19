import os
import logging
from pydantic import BaseModel, model_validator

_config_logger = logging.getLogger("config")

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
    APP_NAME: str = os.getenv("APP_NAME", "Omni FB Analytics") or "Omni FB Analytics"
    DEBUG: bool = (os.getenv("DEBUG", "True") or "True").lower() == "true"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./social_growth.db") or "sqlite:///./social_growth.db"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-autonomous-key-2026") or "super-secret-autonomous-key-2026"
    TOKEN_ENCRYPTION_KEY: str = os.getenv("TOKEN_ENCRYPTION_KEY", "") or ""
    CRON_SECRET: str = os.getenv("CRON_SECRET", "") or ""
    DEMO_MODE: bool = (os.getenv("DEMO_MODE", "False") or "False").lower() == "true"

    FACEBOOK_APP_ID: str = os.getenv("FACEBOOK_APP_ID", "") or ""
    FACEBOOK_CLIENT_SECRET: str = os.getenv("FACEBOOK_CLIENT_SECRET", "") or ""
    FACEBOOK_REDIRECT_URI: str = os.getenv("FACEBOOK_REDIRECT_URI", "") or ""
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "") or ""
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "") or ""

    # Safe int parse: handles empty string env vars gracefully
    AUTONOMOUS_CYCLE_INTERVAL_MINUTES: int = int(os.getenv("AUTONOMOUS_CYCLE_INTERVAL_MINUTES", "60") or "60")

    @model_validator(mode="after")
    def validate_production_safeguards(self) -> "Settings":
        is_prod_env = bool(os.getenv("VERCEL")) or bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
        is_prod = not self.DEBUG or is_prod_env

        if is_prod_env and self.DEBUG:
            _config_logger.warning(
                "WARNING: DEBUG mode is enabled in a production environment (Vercel/Lambda). "
                "Set DEBUG=False in your Vercel environment variables."
            )

        if is_prod and self.SECRET_KEY == "super-secret-autonomous-key-2026":
            _config_logger.warning(
                "WARNING: Using the default SECRET_KEY in production is insecure. "
                "Set a strong, random SECRET_KEY in your Vercel environment variables."
            )

        if is_prod and not self.TOKEN_ENCRYPTION_KEY:
            _config_logger.warning(
                "WARNING: TOKEN_ENCRYPTION_KEY is not set. "
                "Social account tokens will NOT be encrypted. "
                "Generate a Fernet key and set TOKEN_ENCRYPTION_KEY in Vercel environment variables."
            )

        if self.TOKEN_ENCRYPTION_KEY:
            try:
                from cryptography.fernet import Fernet
                Fernet(self.TOKEN_ENCRYPTION_KEY.encode())
            except Exception as e:
                _config_logger.error(
                    f"Invalid TOKEN_ENCRYPTION_KEY: {e}. "
                    "Generate a new key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )
                # Clear invalid key so app can still start without encryption
                object.__setattr__(self, 'TOKEN_ENCRYPTION_KEY', '')

        return self

settings = Settings()
