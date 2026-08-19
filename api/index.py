"""
Diagnostic entry point - catches ALL import errors and returns them as JSON
so we can see exactly what's failing on Vercel.
"""
import sys
import os
import json
import traceback

# Add project root to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

errors = []
app = None

# Step 1: Try importing config
try:
    from backend.config import settings
    errors.append({"step": "config", "status": "OK"})
except Exception as e:
    errors.append({"step": "config", "status": "FAIL", "error": str(e), "trace": traceback.format_exc()})

# Step 2: Try importing database
try:
    from backend.database import Base, engine, init_db
    errors.append({"step": "database", "status": "OK"})
except Exception as e:
    errors.append({"step": "database", "status": "FAIL", "error": str(e), "trace": traceback.format_exc()})

# Step 3: Try importing security
try:
    from backend.security import encrypt_secret, decrypt_secret
    errors.append({"step": "security", "status": "OK"})
except Exception as e:
    errors.append({"step": "security", "status": "FAIL", "error": str(e), "trace": traceback.format_exc()})

# Step 4: Try importing models
try:
    from backend.models import User
    errors.append({"step": "models", "status": "OK"})
except Exception as e:
    errors.append({"step": "models", "status": "FAIL", "error": str(e), "trace": traceback.format_exc()})

# Step 5: Try importing orchestrator
try:
    from backend.orchestrator import orchestrator
    errors.append({"step": "orchestrator", "status": "OK"})
except Exception as e:
    errors.append({"step": "orchestrator", "status": "FAIL", "error": str(e), "trace": traceback.format_exc()})

# Step 6: Try importing the full app
try:
    from backend.main import app as real_app
    app = real_app
    errors.append({"step": "main_app", "status": "OK"})
except Exception as e:
    errors.append({"step": "main_app", "status": "FAIL", "error": str(e), "trace": traceback.format_exc()})

# If any step failed, create a diagnostic FastAPI app
if app is None or any(e["status"] == "FAIL" for e in errors):
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    diag_app = FastAPI(title="Diagnostic Mode")

    @diag_app.get("/{path:path}")
    @diag_app.post("/{path:path}")
    async def diagnostic(path: str):
        return JSONResponse({
            "status": "BOOT_FAILED",
            "python_version": sys.version,
            "root": ROOT,
            "sys_path": sys.path[:5],
            "steps": errors
        }, status_code=500)

    app = diag_app
