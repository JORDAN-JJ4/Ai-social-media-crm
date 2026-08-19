import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), default="Growth Manager")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ConnectedPage(Base):
    __tablename__ = "connected_pages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    facebook_page_id = Column(String(255), index=True)
    facebook_page_name = Column(String(255))
    facebook_access_token = Column(Text)
    instagram_account_id = Column(String(255), nullable=True)
    instagram_account_name = Column(String(255), nullable=True)
    page_category = Column(String(255), default="Technology & AI")
    language = Column(String(50), default="English")
    page_about = Column(Text, nullable=True, default="")
    target_audience = Column(Text, nullable=True, default="General Target Audience")
    growth_goal = Column(Text, nullable=True, default="Brand Awareness & Organic Engagement")
    tone_of_voice = Column(String(255), nullable=True, default="Professional & Engaging")
    custom_instructions = Column(Text, nullable=True, default="")
    is_active_growth = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    facebook_page_id = Column(String(255), nullable=True, default="")
    facebook_access_token = Column(Text, nullable=True, default="")
    instagram_account_id = Column(String(255), nullable=True, default="")
    instagram_access_token = Column(Text, nullable=True, default="")
    page_category = Column(String(255), default="Technology & AI")
    language = Column(String(50), default="English")
    page_about = Column(Text, nullable=True, default="")
    target_audience = Column(Text, nullable=True, default="General Target Audience")
    growth_goal = Column(Text, nullable=True, default="Brand Awareness & Organic Engagement")
    tone_of_voice = Column(String(255), nullable=True, default="Professional & Engaging")
    custom_instructions = Column(Text, nullable=True, default="")
    gemini_api_key = Column(String(255), nullable=True, default="")
    virtux_api_key = Column(String(255), nullable=True, default="")
    auto_mode_enabled = Column(Boolean, default=False)
    timezone = Column(String(100), default="UTC")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)




class TrendMemory(Base):
    __tablename__ = "trend_memory"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(500), index=True)
    category = Column(String(255))
    format_type = Column(String(100), default="Reel") # Reel, Carousel, Single Image, Infographic
    relevance_score = Column(Float, default=0.8)
    summary = Column(Text)
    source_type = Column(String(100), default="AI Research") # News, Viral, Holiday, Seasonal
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Strategy(Base):
    __tablename__ = "strategy"

    id = Column(Integer, primary_key=True, index=True)
    target_date = Column(String(20), index=True) # YYYY-MM-DD
    target_posts_count = Column(Integer, default=2)
    image_ratio = Column(Float, default=0.4)
    reel_ratio = Column(Float, default=0.4)
    carousel_ratio = Column(Float, default=0.2)
    educational_pct = Column(Integer, default=40)
    entertainment_pct = Column(Integer, default=40)
    promotional_pct = Column(Integer, default=20)
    focus_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ContentPost(Base):
    __tablename__ = "content_posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500))
    hook = Column(Text)
    caption = Column(Text)
    cta = Column(String(500))
    hashtags = Column(Text)
    media_type = Column(String(50), default="IMAGE") # IMAGE, REEL, CAROUSEL
    content_angle = Column(String(100), default="EDUCATIONAL") # EDUCATIONAL, ENTERTAINMENT, PROMOTIONAL
    
    image_prompt = Column(Text, nullable=True)
    video_prompt = Column(Text, nullable=True)
    media_urls = Column(JSON, nullable=True) # List of image/video URLs
    
    target_platform = Column(String(50), default="BOTH") # FACEBOOK, INSTAGRAM, BOTH
    status = Column(String(50), default="SCHEDULED") # DRAFT, SCHEDULED, PUBLISHING, PUBLISHED, FAILED
    scheduled_time = Column(DateTime, index=True)
    published_time = Column(DateTime, nullable=True)
    
    meta_facebook_post_id = Column(String(255), nullable=True)
    meta_instagram_post_id = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    publishing_logs = relationship("PublishingLog", back_populates="post", cascade="all, delete-orphan")
    analytics = relationship("AnalyticsData", back_populates="post", cascade="all, delete-orphan")


class PublishingLog(Base):
    __tablename__ = "publishing_logs"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("content_posts.id"))
    platform = Column(String(50)) # FACEBOOK, INSTAGRAM
    status = Column(String(50)) # SUCCESS, FAILED, RETRYING
    attempt_count = Column(Integer, default=1)
    message = Column(Text)
    response_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    post = relationship("ContentPost", back_populates="publishing_logs")


class AnalyticsData(Base):
    __tablename__ = "analytics_data"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("content_posts.id"), nullable=True)
    platform = Column(String(50), default="BOTH")
    reach = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    watch_time_seconds = Column(Integer, default=0)
    follower_growth = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow)

    post = relationship("ContentPost", back_populates="analytics")


class AgentMemory(Base):
    __tablename__ = "agent_memory"

    id = Column(Integer, primary_key=True, index=True)
    memory_key = Column(String(100), index=True) # e.g. "top_performing_hooks", "best_posting_times", "failed_topics"
    category = Column(String(255), default="General")
    content = Column(JSON) # Structured memory dictionary or list
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(100), index=True)
    level = Column(String(20), default="INFO") # INFO, SUCCESS, WARNING, ERROR
    action = Column(String(255))
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
