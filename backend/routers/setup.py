import os
import asyncio
import urllib.parse
import httpx
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from backend.database import get_db
from backend.config import settings as app_settings
from backend.models import SystemSettings, ConnectedPage
from backend.schemas import SetupConfigRequest, SetupConfigResponse
from backend.orchestrator import orchestrator

logger = logging.getLogger("setup_router")
router = APIRouter(prefix="", tags=["Setup & Settings"])

def update_env_variable(key: str, value: str, filepath=".env"):
    try:
        lines = []
        found = False
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith(f"{key}="):
                        lines.append(f'{key}="{value}"\n')
                        found = True
                    else:
                        lines.append(line)
        if not found:
            lines.append(f'{key}="{value}"\n')
            
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)
        os.environ[key] = value
    except Exception as e:
        logger.error(f"Failed updating .env variable {key}: {e}")

class PageGrowthUpdateItem(BaseModel):
    facebook_page_id: str
    facebook_page_name: str
    facebook_access_token: str
    instagram_account_id: Optional[str] = ""
    instagram_account_name: Optional[str] = ""
    page_category: str = "Technology & AI"
    language: str = "English"
    page_about: Optional[str] = ""
    target_audience: Optional[str] = "General Target Audience"
    growth_goal: Optional[str] = "Brand Awareness & Organic Engagement"
    tone_of_voice: Optional[str] = "Professional & Engaging"
    custom_instructions: Optional[str] = ""
    is_active_growth: bool = True

class PageTargetGoalRequest(BaseModel):
    page_about: Optional[str] = ""
    target_audience: Optional[str] = "General Target Audience"
    growth_goal: Optional[str] = "Brand Awareness & Organic Engagement"
    tone_of_voice: Optional[str] = "Professional & Engaging"
    custom_instructions: Optional[str] = ""
    page_category: Optional[str] = "Technology & AI"
    language: Optional[str] = "English"



@router.get("/api/setup", response_model=SetupConfigResponse)
def get_setup(db = Depends(get_db)):
    stmt = select(SystemSettings).order_by(SystemSettings.id.desc())
    res = db.execute(stmt)
    settings = res.scalars().first()
    if not settings:
        settings = SystemSettings(
            page_category="Technology & AI",
            language="English",
            auto_mode_enabled=True,
            gemini_api_key=app_settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    else:
        if not settings.gemini_api_key:
            settings.gemini_api_key = app_settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    return settings

@router.post("/api/setup", response_model=SetupConfigResponse)
def save_setup(payload: SetupConfigRequest, db = Depends(get_db)):
    stmt = select(SystemSettings).order_by(SystemSettings.id.desc())
    res = db.execute(stmt)
    settings = res.scalars().first()

    if not settings:
        settings = SystemSettings()

    settings.facebook_page_id = payload.facebook_page_id or ""
    settings.facebook_access_token = payload.facebook_access_token or ""
    settings.instagram_account_id = payload.instagram_account_id or ""
    settings.instagram_access_token = payload.instagram_access_token or ""
    settings.page_category = payload.page_category
    settings.language = payload.language
    settings.gemini_api_key = payload.gemini_api_key or ""
    settings.virtux_api_key = payload.virtux_api_key or ""
    settings.auto_mode_enabled = payload.auto_mode_enabled
    settings.timezone = payload.timezone

    if payload.gemini_api_key:
        update_env_variable("GEMINI_API_KEY", payload.gemini_api_key)

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings

@router.get("/api/setup/pages")
def get_connected_pages(db = Depends(get_db)):
    stmt = select(ConnectedPage).order_by(ConnectedPage.id.desc())
    res = db.execute(stmt)
    pages = res.scalars().all()
    return pages

@router.post("/api/setup/pages")
def save_connected_pages(pages_list: List[PageGrowthUpdateItem], db = Depends(get_db)):
    for p in pages_list:
        stmt = select(ConnectedPage).where(ConnectedPage.facebook_page_id == p.facebook_page_id)
        res = db.execute(stmt)
        existing = res.scalars().first()

        if existing:
            existing.page_category = p.page_category
            existing.language = p.language
            existing.is_active_growth = p.is_active_growth
            db.add(existing)
        else:
            new_p = ConnectedPage(
                facebook_page_id=p.facebook_page_id,
                facebook_page_name=p.facebook_page_name,
                facebook_access_token=p.facebook_access_token,
                instagram_account_id=p.instagram_account_id or "",
                instagram_account_name=p.instagram_account_name or "",
                page_category=p.page_category,
                language=p.language,
                is_active_growth=True
            )
            db.add(new_p)

    db.commit()
    return {"status": "SUCCESS", "updated": len(pages_list)}

@router.post("/api/setup/pages/{facebook_page_id}/target")
def save_page_target_goal(facebook_page_id: str, payload: PageTargetGoalRequest, db = Depends(get_db)):
    stmt = select(ConnectedPage).where(ConnectedPage.facebook_page_id == facebook_page_id)
    res = db.execute(stmt)
    page = res.scalars().first()
    if not page:
        raise HTTPException(status_code=404, detail="Connected page not found")

    page.page_about = payload.page_about or page.page_about or ""
    page.target_audience = payload.target_audience
    page.growth_goal = payload.growth_goal
    page.tone_of_voice = payload.tone_of_voice
    page.custom_instructions = payload.custom_instructions
    if payload.page_category:
        page.page_category = payload.page_category
    if payload.language:
        page.language = payload.language
    db.add(page)

    # Sync with SystemSettings
    s_stmt = select(SystemSettings).order_by(SystemSettings.id.desc())
    settings = db.execute(s_stmt).scalars().first()
    if not settings:
        settings = SystemSettings()
    
    settings.facebook_page_id = page.facebook_page_id
    settings.facebook_access_token = page.facebook_access_token
    settings.page_category = page.page_category
    settings.language = page.language
    settings.page_about = page.page_about
    settings.target_audience = page.target_audience
    settings.growth_goal = page.growth_goal
    settings.tone_of_voice = page.tone_of_voice
    settings.custom_instructions = page.custom_instructions
    settings.auto_mode_enabled = True
    db.add(settings)

    db.commit()
    return {"status": "SUCCESS", "message": f"Target growth goal updated for '{page.facebook_page_name}'!"}

@router.get("/api/setup/cron-tick")
async def vercel_cron_tick(db = Depends(get_db)):
    """
    Vercel Free Cron Job endpoint triggered automatically every hour on Vercel Serverless.
    """
    from backend.orchestrator import orchestrator
    res = await orchestrator.run_full_autonomous_cycle(force=True)
    return {"status": "SUCCESS", "cron_result": res}

@router.post("/api/setup/pages/{facebook_page_id}/trigger")
async def trigger_page_growth_pipeline(facebook_page_id: str, db = Depends(get_db)):
    stmt = select(ConnectedPage).where(ConnectedPage.facebook_page_id == facebook_page_id)
    res = db.execute(stmt)
    page = res.scalars().first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    page.is_active_growth = True
    db.add(page)

    # Set as primary page in SystemSettings
    s_stmt = select(SystemSettings).order_by(SystemSettings.id.desc())
    s_res = db.execute(s_stmt)
    settings = s_res.scalars().first()
    if not settings:
        settings = SystemSettings()
    
    settings.facebook_page_id = page.facebook_page_id
    settings.facebook_access_token = page.facebook_access_token
    settings.page_category = page.page_category
    settings.language = page.language
    settings.page_about = page.page_about
    settings.target_audience = page.target_audience
    settings.growth_goal = page.growth_goal
    settings.tone_of_voice = page.tone_of_voice
    settings.custom_instructions = page.custom_instructions
    settings.auto_mode_enabled = True
    if not settings.gemini_api_key:
        settings.gemini_api_key = app_settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    db.add(settings)
    db.commit()


    # Trigger full 8 agent pipeline in background using asyncio
    asyncio.create_task(orchestrator.run_full_autonomous_cycle(force=True))

    return {
        "status": "SUCCESS",
        "message": f"AI Growth Pipeline launched for page '{page.facebook_page_name}'!",
        "page_id": page.facebook_page_id
    }


@router.delete("/api/setup/pages/{facebook_page_id}")
def delete_connected_page(facebook_page_id: str, db = Depends(get_db)):
    stmt = select(ConnectedPage).where(ConnectedPage.facebook_page_id == facebook_page_id)
    res = db.execute(stmt)
    page = res.scalars().first()
    if not page:
        raise HTTPException(status_code=404, detail="Connected page not found")
    
    db.delete(page)
    
    # If primary system setting page was this page, clear or update it
    stmt_s = select(SystemSettings).order_by(SystemSettings.id.desc())
    s_res = db.execute(stmt_s)
    settings_obj = s_res.scalars().first()
    if settings_obj and settings_obj.facebook_page_id == facebook_page_id:
        remaining_stmt = select(ConnectedPage).where(ConnectedPage.facebook_page_id != facebook_page_id)
        rem = db.execute(remaining_stmt).scalars().first()
        if rem:
            settings_obj.facebook_page_id = rem.facebook_page_id
            settings_obj.facebook_access_token = rem.facebook_access_token
        else:
            settings_obj.facebook_page_id = ""
            settings_obj.facebook_access_token = ""
        db.add(settings_obj)

    db.commit()
    return {"status": "SUCCESS", "message": f"Page {facebook_page_id} disconnected successfully."}

@router.get("/api/setup/env")
def get_env_credentials():
    return {
        "facebook_app_id": app_settings.FACEBOOK_APP_ID,
        "facebook_redirect_uri": app_settings.FACEBOOK_REDIRECT_URI,
        "has_app_secret": bool(app_settings.FACEBOOK_CLIENT_SECRET)
    }

@router.get("/api/setup/facebook/login_url")
def get_facebook_login_url():
    app_id = app_settings.FACEBOOK_APP_ID
    redirect_uri = app_settings.FACEBOOK_REDIRECT_URI or "http://localhost:8000/auth/facebook/callback"
    scope = "public_profile,pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish"
    
    url = (
        f"https://www.facebook.com/v19.0/dialog/oauth?"
        f"client_id={app_id}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
        f"scope={urllib.parse.quote(scope)}&"
        f"response_type=code"
    )
    return {"login_url": url}

@router.get("/auth/facebook/callback")
async def facebook_oauth_callback(code: str = Query(...), db = Depends(get_db)):
    app_id = app_settings.FACEBOOK_APP_ID
    app_secret = app_settings.FACEBOOK_CLIENT_SECRET
    redirect_uri = app_settings.FACEBOOK_REDIRECT_URI or "http://localhost:8000/auth/facebook/callback"

    token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
    params = {
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "client_secret": app_secret,
        "code": code
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(token_url, params=params)
            if res.status_code != 200:
                logger.error(f"Failed exchanging code for access token: {res.text}")
                return HTMLResponse(content=f"<h3>Facebook Auth Error</h3><p>{res.text}</p>", status_code=400)
            
            token_data = res.json()
            user_access_token = token_data.get("access_token")

            pages_url = "https://graph.facebook.com/v19.0/me/accounts?fields=id,name,access_token,category,instagram_business_account"
            pages_res = await client.get(f"{pages_url}&access_token={user_access_token}")
            
            pages = []
            if pages_res.status_code == 200:
                pages_data = pages_res.json()
                pages = pages_data.get("data", [])

            # Save discovered pages into ConnectedPage database table
            for p in pages:
                p_id = p.get("id")
                p_name = p.get("name", "Facebook Page")
                p_token = p.get("access_token", "")
                p_cat = p.get("category", "Technology & AI")
                
                ig_id = ""
                ig_obj = p.get("instagram_business_account")
                if ig_obj and isinstance(ig_obj, dict):
                    ig_id = ig_obj.get("id", "")

                stmt_p = select(ConnectedPage).where(ConnectedPage.facebook_page_id == p_id)
                res_p = db.execute(stmt_p)
                existing_p = res_p.scalars().first()

                if existing_p:
                    existing_p.facebook_page_name = p_name
                    existing_p.facebook_access_token = p_token
                    existing_p.instagram_account_id = ig_id
                    existing_p.page_category = p_cat
                    db.add(existing_p)
                else:
                    new_p = ConnectedPage(
                        facebook_page_id=p_id,
                        facebook_page_name=p_name,
                        facebook_access_token=p_token,
                        instagram_account_id=ig_id,
                        page_category=p_cat,
                        is_active_growth=True
                    )
                    db.add(new_p)

            # Also update SystemSettings with primary page if available
            if pages:
                first_page = pages[0]
                stmt = select(SystemSettings).order_by(SystemSettings.id.desc())
                s_res = db.execute(stmt)
                settings_obj = s_res.scalars().first()
                if not settings_obj:
                    settings_obj = SystemSettings()

                settings_obj.facebook_page_id = first_page.get("id", "")
                settings_obj.facebook_access_token = first_page.get("access_token", "")
                settings_obj.page_category = first_page.get("category", "Technology & AI")

                ig_obj = first_page.get("instagram_business_account")
                if ig_obj and isinstance(ig_obj, dict):
                    settings_obj.instagram_account_id = ig_obj.get("id", "")
                    settings_obj.instagram_access_token = first_page.get("access_token", "")

                db.add(settings_obj)

            db.commit()

            html_content = f"""
            <html>
            <body style="font-family:sans-serif;background:#0b0f19;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;">
                <div style="text-align:center;background:#1e293b;padding:40px;border-radius:16px;border:1px solid #334155;">
                    <h2 style="color:#10b981;">✅ Discovered & Connected {len(pages)} Facebook Pages!</h2>
                    <p>Redirecting to Page Selection & Setup Wizard...</p>
                    <script>
                        setTimeout(function() {{
                            if (window.opener) {{
                                window.opener.location.reload();
                                window.close();
                            }} else {{
                                window.location.href = '/';
                            }}
                        }}, 1500);
                    </script>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content)

    except Exception as e:
        logger.error(f"Error in Facebook OAuth Callback: {e}")
        return HTMLResponse(content=f"<h3>Authentication Exception</h3><p>{str(e)}</p>", status_code=500)
