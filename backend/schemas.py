import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

# --- Settings Schemas ---
class SetupConfigRequest(BaseModel):
    facebook_page_id: Optional[str] = ""
    facebook_access_token: Optional[str] = ""
    instagram_account_id: Optional[str] = ""
    instagram_access_token: Optional[str] = ""
    page_category: str = "Technology & AI"
    language: str = "English"
    gemini_api_key: Optional[str] = ""
    virtux_api_key: Optional[str] = ""
    auto_mode_enabled: bool = False
    timezone: str = "UTC"

class SetupConfigResponse(SetupConfigRequest):
    id: int
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

# --- Post Schemas ---
class PostBase(BaseModel):
    title: str
    hook: str
    caption: str
    cta: str
    hashtags: str
    media_type: str = "IMAGE"
    content_angle: str = "EDUCATIONAL"
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    media_urls: Optional[List[str]] = []
    target_platform: str = "BOTH"
    scheduled_time: datetime.datetime

class PostCreate(PostBase):
    pass

class PostResponse(PostBase):
    id: int
    status: str
    published_time: Optional[datetime.datetime] = None
    meta_facebook_post_id: Optional[str] = None
    meta_instagram_post_id: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# --- Analytics Schemas ---
class AnalyticsOverviewResponse(BaseModel):
    total_followers: int
    total_reach: int
    total_likes: int
    total_comments: int
    total_shares: int
    total_saves: int
    total_watch_time: int
    avg_engagement_rate: float
    best_posting_hour: str
    top_media_type: str
    posts_published_count: int

# --- Agent Status Schema ---
class AgentStatusItem(BaseModel):
    agent_name: str
    display_name: str
    status: str # IDLE, RUNNING, COMPLETED, ERROR
    last_run: Optional[str] = None
    last_action: str
    metrics_summary: str

class AgentStatusListResponse(BaseModel):
    agents: List[AgentStatusItem]
    auto_mode: bool
    last_cycle_timestamp: Optional[str] = None

# --- Log Schema ---
class SystemLogResponse(BaseModel):
    id: int
    agent_name: str
    level: str
    action: str
    details: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True
