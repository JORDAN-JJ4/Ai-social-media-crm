"""
Diagnostic entry point - catches ALL import errors and returns them as JSON.
"""
import sys
import os
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

errors = []
app = None

try:
    from backend.config import settings
    errors.append({"step": "config", "status": "OK", "DATABASE_URL": repr(settings.DATABASE_URL)})
except Exception as e:
    errors.append({"step": "config", "status": "FAIL", "error": str(e)})

try:
    import backend.database as _db_mod
    errors.append({"step": "database", "status": "OK", "db_url": _db_mod.db_url})
except Exception as e:
    errors.append({"step": "database", "status": "FAIL", "error": str(e), "trace": traceback.format_exc()})

try:
    from backend.models import User
    errors.append({"step": "models", "status": "OK"})
except Exception as e:
    errors.append({"step": "models", "status": "FAIL", "error": str(e)})

try:
    from backend.main import app as real_app
    app = real_app
    errors.append({"step": "main_app", "status": "OK"})
except Exception as e:
    errors.append({"step": "main_app", "status": "FAIL", "error": str(e), "trace": traceback.format_exc()})

if app is None or any(e["status"] == "FAIL" for e in errors):
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    diag_app = FastAPI(title="Diagnostic")

    @diag_app.get("/{path:path}")
    @diag_app.post("/{path:path}")
    async def diagnostic(path: str):
        return JSONResponse({
            "status": "BOOT_FAILED",
            "python_version": sys.version,
            "root": ROOT,
            "vercel_env": os.getenv("VERCEL", "not_set"),
            "database_url_raw": os.getenv("DATABASE_URL", "NOT_SET"),
            "steps": errors
        }, status_code=500)

    app = diag_app
