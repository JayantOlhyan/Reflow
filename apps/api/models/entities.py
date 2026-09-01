import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from database import Base

class Content(Base):
    __tablename__ = "contents"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content_type = Column(String(32), nullable=False, index=True)  # VIDEO, IMAGE, PDF, TEXT
    status = Column(String(32), default="READY", index=True)       # UPLOADING, PROCESSING, READY, FAILED
    text_content = Column(Text, nullable=True)                    # For direct text / markdown notes
    thumbnail_path = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relational Associations
    assets = relationship("Asset", back_populates="content", cascade="all, delete-orphan", lazy="selectin")
    variants = relationship("ContentVariant", back_populates="content", cascade="all, delete-orphan", lazy="selectin")
    transcripts = relationship("Transcript", back_populates="content", cascade="all, delete-orphan", lazy="selectin")
    briefs = relationship("ContentBrief", back_populates="content", cascade="all, delete-orphan", lazy="selectin")
    generated_contents = relationship("GeneratedContent", back_populates="content", cascade="all, delete-orphan", lazy="selectin")
    carousels = relationship("Carousel", back_populates="content", cascade="all, delete-orphan", lazy="selectin")
    clips = relationship("Clip", back_populates="content", cascade="all, delete-orphan", lazy="selectin")
    publications = relationship("Publication", back_populates="content", cascade="all, delete-orphan", lazy="selectin")

class Asset(Base):
    __tablename__ = "assets"

    id = Column(String(64), primary_key=True, index=True)
    content_id = Column(String(64), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    storage_key = Column(String(512), nullable=False)
    mime_type = Column(String(128), nullable=False)
    file_size = Column(Integer, default=0)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration = Column(Integer, nullable=True)
    fps = Column(Integer, nullable=True)
    codec = Column(String(64), nullable=True)
    bitrate = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    content = relationship("Content", back_populates="assets")

class ContentVariant(Base):
    __tablename__ = "content_variants"

    id = Column(String(64), primary_key=True, index=True)
    content_id = Column(String(64), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, index=True)
    source_asset_id = Column(String(64), nullable=True)
    variant_type = Column(String(64), nullable=False, index=True)  # THUMBNAIL, LANDSCAPE_16_9, VERTICAL_9_16, SQUARE_1_1, PORTRAIT_4_5, ORIGINAL
    storage_key = Column(String(512), nullable=False)
    mime_type = Column(String(128), nullable=False)
    file_size = Column(Integer, default=0)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration = Column(Integer, nullable=True)
    fps = Column(Integer, nullable=True)
    codec = Column(String(64), nullable=True)
    status = Column(String(32), default="READY", index=True)       # QUEUED, PROCESSING, READY, FAILED
    created_at = Column(DateTime, default=datetime.utcnow)

    content = relationship("Content", back_populates="variants")

class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(String(64), primary_key=True, index=True)
    content_id = Column(String(64), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(String(64), nullable=True)
    provider = Column(String(32), default="mock")
    language = Column(String(16), default="en")
    text = Column(Text, nullable=False)
    duration = Column(Float, nullable=True)
    status = Column(String(32), default="READY", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    content = relationship("Content", back_populates="transcripts")
    segments = relationship("TranscriptSegment", back_populates="transcript", cascade="all, delete-orphan", lazy="selectin")

class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id = Column(String(64), primary_key=True, index=True)
    transcript_id = Column(String(64), ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)

    transcript = relationship("Transcript", back_populates="segments")

class ContentBrief(Base):
    __tablename__ = "content_briefs"

    id = Column(String(64), primary_key=True, index=True)
    content_id = Column(String(64), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, index=True)
    transcript_id = Column(String(64), ForeignKey("transcripts.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    topics_json = Column(Text, default="[]")
    keywords_json = Column(Text, default="[]")
    audience = Column(String(255), default="General Audience")
    tone = Column(String(64), default="Professional")
    key_points_json = Column(Text, default="[]")
    hooks_json = Column(Text, default="[]")
    quotes_json = Column(Text, default="[]")
    cta_suggestions_json = Column(Text, default="[]")
    provider = Column(String(32), default="mock")
    model = Column(String(64), default="mock-model")
    prompt_version = Column(String(32), default="v1")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    content = relationship("Content", back_populates="briefs")

    @property
    def topics(self):
        try: return json.loads(self.topics_json)
        except: return []

    @property
    def keywords(self):
        try: return json.loads(self.keywords_json)
        except: return []

    @property
    def key_points(self):
        try: return json.loads(self.key_points_json)
        except: return []

    @property
    def hooks(self):
        try: return json.loads(self.hooks_json)
        except: return []

    @property
    def quotes(self):
        try: return json.loads(self.quotes_json)
        except: return []

    @property
    def cta_suggestions(self):
        try: return json.loads(self.cta_suggestions_json)
        except: return []

class GeneratedContent(Base):
    __tablename__ = "generated_contents"

    id = Column(String(64), primary_key=True, index=True)
    content_id = Column(String(64), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, index=True)
    brief_id = Column(String(64), ForeignKey("content_briefs.id", ondelete="CASCADE"), nullable=True)
    platform = Column(String(32), nullable=False, index=True)      # LINKEDIN, INSTAGRAM, X, YOUTUBE
    generation_type = Column(String(64), nullable=False)           # POST, THREAD, REEL_CAPTION, VIDEO_METADATA
    status = Column(String(32), default="READY", index=True)       # GENERATING, READY, FAILED
    content_payload_json = Column(Text, nullable=False)
    provider = Column(String(32), default="mock")
    model = Column(String(64), default="mock-model")
    prompt_version = Column(String(32), default="v1")
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    content = relationship("Content", back_populates="generated_contents")

    @property
    def payload(self):
        try: return json.loads(self.content_payload_json)
        except: return {}

# ------------------------------------------------------------------------------
# Phase 4 Carousel Engine Entities
# ------------------------------------------------------------------------------

class Carousel(Base):
    __tablename__ = "carousels"

    id = Column(String(64), primary_key=True, index=True)
    content_id = Column(String(64), ForeignKey("contents.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    status = Column(String(32), default="READY", index=True)       # DRAFT, GENERATING, READY, FAILED, RENDERING
    aspect_ratio = Column(String(16), default="1:1")               # 1:1, 4:5
    template = Column(String(32), default="MINIMAL")               # MINIMAL, EDITORIAL, BOLD, EDUCATIONAL
    slide_count = Column(Integer, default=0)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    content = relationship("Content", back_populates="carousels")
    slides = relationship("CarouselSlide", back_populates="carousel", cascade="all, delete-orphan", order_by="CarouselSlide.position", lazy="selectin")
    exports = relationship("CarouselExport", back_populates="carousel", cascade="all, delete-orphan", lazy="selectin")

class CarouselSlide(Base):
    __tablename__ = "carousel_slides"

    id = Column(String(64), primary_key=True, index=True)
    carousel_id = Column(String(64), ForeignKey("carousels.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, nullable=False, index=True)
    purpose = Column(String(32), default="KEY_POINT")              # HOOK, PROBLEM, INSIGHT, KEY_POINT, EXAMPLE, STATISTIC, QUOTE, FRAMEWORK, SUMMARY, CTA
    layout = Column(String(32), default="TITLE_BODY")              # TITLE, TITLE_BODY, FULL_IMAGE, QUOTE, STATISTIC, TWO_COLUMN, FRAMEWORK, CTA
    headline = Column(String(255), nullable=False, default="")
    body = Column(Text, nullable=False, default="")
    tag = Column(String(64), nullable=True, default="")
    background = Column(String(64), default="#0F172A")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    carousel = relationship("Carousel", back_populates="slides")
    elements = relationship("SlideElement", back_populates="slide", cascade="all, delete-orphan", lazy="selectin")

class SlideElement(Base):
    __tablename__ = "slide_elements"

    id = Column(String(64), primary_key=True, index=True)
    slide_id = Column(String(64), ForeignKey("carousel_slides.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(32), nullable=False)                      # TEXT, IMAGE, SHAPE, ICON
    position_x = Column(Float, default=0.0)
    position_y = Column(Float, default=0.0)
    width = Column(Float, default=100.0)
    height = Column(Float, default=100.0)
    content = Column(Text, default="")
    style_json = Column(Text, default="{}")
    z_index = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    slide = relationship("CarouselSlide", back_populates="elements")

    @property
    def style(self):
        try: return json.loads(self.style_json)
        except: return {}

class CarouselExport(Base):
    __tablename__ = "carousel_exports"

    id = Column(String(64), primary_key=True, index=True)
    carousel_id = Column(String(64), ForeignKey("carousels.id", ondelete="CASCADE"), nullable=False, index=True)
    carousel_version = Column(Integer, default=1)
    format = Column(String(16), nullable=False)                    # PNG, JPG, PDF
    storage_key = Column(String(512), nullable=False)
    file_size = Column(Integer, default=0)
    status = Column(String(32), default="READY", index=True)       # GENERATING, READY, FAILED
    created_at = Column(DateTime, default=datetime.utcnow)

    carousel = relationship("Carousel", back_populates="exports")

# ------------------------------------------------------------------------------
# Phase 5 Intelligent Clip Engine Entities
# ------------------------------------------------------------------------------

class Clip(Base):
    __tablename__ = "clips"

    id = Column(String(64), primary_key=True, index=True)
    content_id = Column(String(64), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, index=True)
    source_asset_id = Column(String(64), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    hook = Column(String(512), default="")
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)
    status = Column(String(32), default="CANDIDATE", index=True)   # CANDIDATE, SELECTED, PROCESSING, READY, FAILED
    score = Column(Float, default=80.0)
    reason = Column(Text, default="")
    source_transcript_segment_ids_json = Column(Text, default="[]")
    transcript_excerpt = Column(Text, default="")
    thumbnail_path = Column(String(512), nullable=True)
    discovery_version = Column(String(32), default="v1")
    caption_style = Column(String(64), default="BOLD_PUNCH")      # BOLD_PUNCH, CLEAN_SUBTITLE, KINETIC_HIGHLIGHT, MINIMAL_WHITE
    caption_enabled = Column(Boolean, default=True)
    highlight_keywords_json = Column(Text, default="[]")
    caption_custom_settings_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    content = relationship("Content", back_populates="clips")
    variants = relationship("ClipVariant", back_populates="clip", cascade="all, delete-orphan", lazy="selectin")

    @property
    def source_transcript_segment_ids(self):
        try: return json.loads(self.source_transcript_segment_ids_json)
        except: return []

    @property
    def highlight_keywords(self):
        try: return json.loads(self.highlight_keywords_json)
        except: return []

    @property
    def caption_custom_settings(self):
        try: return json.loads(self.caption_custom_settings_json)
        except: return {}

class ClipVariant(Base):
    __tablename__ = "clip_variants"

    id = Column(String(64), primary_key=True, index=True)
    clip_id = Column(String(64), ForeignKey("clips.id", ondelete="CASCADE"), nullable=False, index=True)
    variant_type = Column(String(64), nullable=False, index=True)  # MASTER, VERTICAL_9_16, SQUARE_1_1, PORTRAIT_4_5, LANDSCAPE_16_9, THUMBNAIL, CAPTIONED_VERTICAL_9_16, etc.
    aspect_ratio = Column(String(16), default="9:16")              # 9:16, 1:1, 4:5, 16:9
    storage_key = Column(String(512), nullable=False)
    mime_type = Column(String(128), default="video/mp4")
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration = Column(Float, nullable=True)
    file_size = Column(Integer, default=0)
    has_captions = Column(Boolean, default=False)
    caption_style = Column(String(64), nullable=True)
    status = Column(String(32), default="READY", index=True)       # QUEUED, PROCESSING, READY, FAILED
    created_at = Column(DateTime, default=datetime.utcnow)

    clip = relationship("Clip", back_populates="variants")

class PlatformConnection(Base):
    __tablename__ = "platform_connections"

    id = Column(String(64), primary_key=True, index=True)
    platform = Column(String(32), nullable=False, index=True)      # youtube, instagram, linkedin, x, facebook, tiktok, pinterest, threads
    name = Column(String(128), nullable=False)
    account_name = Column(String(128), default="")
    handle = Column(String(128), default="")
    external_account_id = Column(String(128), nullable=True, index=True)
    status = Column(String(32), default="CONNECTED", index=True)   # CONNECTED, DISCONNECTED, REAUTH_REQUIRED, EXPIRED
    avatar_url = Column(String(512), default="")
    access_token_encrypted = Column(Text, nullable=True)
    refresh_token_encrypted = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    scopes_json = Column(Text, default="[]")
    capabilities_json = Column(Text, default="[]")
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    publications = relationship("Publication", back_populates="connection")

    @property
    def capabilities(self):
        try: return json.loads(self.capabilities_json)
        except: return []

    @property
    def scopes(self):
        try: return json.loads(self.scopes_json)
        except: return []

    @property
    def metadata_dict(self):
        try: return json.loads(self.metadata_json)
        except: return {}

class Publication(Base):
    __tablename__ = "publications"

    id = Column(String(64), primary_key=True, index=True)
    content_id = Column(String(64), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, index=True)
    variant_id = Column(String(64), nullable=True, index=True)
    platform_connection_id = Column(String(64), ForeignKey("platform_connections.id", ondelete="SET NULL"), nullable=True, index=True)
    platform = Column(String(32), nullable=False, index=True)      # youtube, instagram, linkedin, x, etc.
    status = Column(String(32), default="DRAFT", index=True)       # DRAFT, SCHEDULED, QUEUED, UPLOADING, PUBLISHING, PUBLISHED, FAILED, REAUTH_REQUIRED, CANCELLED
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    privacy = Column(String(32), default="PRIVATE")                # PRIVATE, UNLISTED, PUBLIC
    tags_json = Column(Text, default="[]")
    external_post_id = Column(String(128), nullable=True, index=True)
    external_url = Column(String(512), nullable=True)
    request_payload_hash = Column(String(64), nullable=False, index=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    attempt_count = Column(Integer, default=0)
    
    # Phase 9: Scheduling & Claim fields
    scheduled_at = Column(DateTime, nullable=True, index=True)     # Canonical UTC timestamp
    timezone = Column(String(64), nullable=True)                   # Canonical IANA timezone, e.g. "Asia/Kolkata"
    claimed_at = Column(DateTime, nullable=True)                   # Timestamp when scheduler acquired lock lease
    claim_owner = Column(String(64), nullable=True)                # Scheduler instance ID that holds claim
    cancelled_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)

    # Phase 10: Analytics tracking state
    analytics_status = Column(String(32), default="NOT_SYNCED", index=True) # NOT_SYNCED, SYNCING, AVAILABLE, PARTIAL, UNAVAILABLE, FAILED, REAUTH_REQUIRED
    last_analytics_sync_at = Column(DateTime, nullable=True)
    analytics_error_code = Column(String(64), nullable=True)
    analytics_error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_publications_status_scheduled_at", "status", "scheduled_at"),
    )

    content = relationship("Content", back_populates="publications")
    connection = relationship("PlatformConnection", back_populates="publications")
    snapshots = relationship("PostMetricSnapshot", back_populates="publication", cascade="all, delete-orphan", order_by="PostMetricSnapshot.captured_at.desc()", lazy="selectin")

    @property
    def tags(self):
        try: return json.loads(self.tags_json)
        except: return []

class PostMetricSnapshot(Base):
    __tablename__ = "post_metric_snapshots"

    id = Column(String(64), primary_key=True, index=True)
    publication_id = Column(String(64), ForeignKey("publications.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(32), nullable=False, index=True)
    external_post_id = Column(String(128), nullable=True, index=True)
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Standardized typed metric fields (all nullable; NULL means unavailable from API, 0 means reported zero)
    views = Column(Integer, nullable=True)
    impressions = Column(Integer, nullable=True)
    reach = Column(Integer, nullable=True)
    likes = Column(Integer, nullable=True)
    comments = Column(Integer, nullable=True)
    shares = Column(Integer, nullable=True)
    saves = Column(Integer, nullable=True)
    clicks = Column(Integer, nullable=True)
    reposts = Column(Integer, nullable=True)
    replies = Column(Integer, nullable=True)
    engagements = Column(Integer, nullable=True)
    watch_time_seconds = Column(Float, nullable=True)
    average_watch_time_seconds = Column(Float, nullable=True)
    completion_rate = Column(Float, nullable=True)
    followers_gained = Column(Integer, nullable=True)

    raw_metrics_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_snapshots_pub_captured", "publication_id", "captured_at"),
        Index("ix_snapshots_platform_captured", "platform", "captured_at"),
    )

    publication = relationship("Publication", back_populates="snapshots")

    @property
    def raw_metrics(self):
        try: return json.loads(self.raw_metrics_json)
        except: return {}

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    active = Column(Boolean, default=True)
    description = Column(String(512), default="")
    trigger = Column(String(64), default="Manual Upload")
    nodes_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(64), primary_key=True, index=True)
    content_id = Column(String(64), nullable=True, index=True)
    asset_id = Column(String(64), nullable=True)
    type = Column(String(64), nullable=False)                      # MEDIA_PROCESSING, TRANSCRIPTION, CONTENT_ANALYSIS, CONTENT_GENERATION, CAROUSEL_GENERATION, CAROUSEL_RENDER
    status = Column(String(32), default="QUEUED", index=True)       # QUEUED, RUNNING, SUCCEEDED, FAILED, RETRYING, CANCELLED
    payload_json = Column(Text, default="{}")
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(String(64), primary_key=True, index=True)
    level = Column(String(16), default="INFO")
    service = Column(String(64), default="System")
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

# ------------------------------------------------------------------------------
# Phase 11: Content Intelligence & Recommendation Entities
# ------------------------------------------------------------------------------

class PerformanceInsight(Base):
    __tablename__ = "performance_insights"

    id = Column(String(64), primary_key=True, index=True)
    type = Column(String(64), nullable=False, index=True)          # FORMAT_PERFORMANCE, HOOK_PERFORMANCE, TOPIC_PERFORMANCE, DURATION_PERFORMANCE, POSTING_TIME_PERFORMANCE, OUTLIER_BREAKOUT
    scope = Column(String(32), default="ACCOUNT", index=True)      # ACCOUNT, PLATFORM, CONTENT_TYPE, TOPIC, CLIP, CAROUSEL
    platform = Column(String(32), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    evidence_json = Column(Text, default="{}")
    sample_size = Column(Integer, default=0)
    confidence = Column(String(32), default="MEDIUM")              # HIGH, MEDIUM, LOW, INSUFFICIENT_DATA
    source_metric = Column(String(64), default="engagement_rate")
    baseline_value = Column(Float, nullable=True)
    observed_value = Column(Float, nullable=True)
    delta_pct = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    @property
    def evidence(self):
        try: return json.loads(self.evidence_json)
        except: return {}

class ContentPattern(Base):
    __tablename__ = "content_patterns"

    id = Column(String(64), primary_key=True, index=True)
    pattern_type = Column(String(64), nullable=False, index=True)  # HOOK, TOPIC, DURATION_BUCKET, POSTING_WINDOW, TEMPLATE, FEATURE
    feature_name = Column(String(128), nullable=False, index=True)
    feature_value = Column(String(128), nullable=False, index=True)
    sample_size = Column(Integer, default=0)
    median_views = Column(Float, nullable=True)
    median_engagement_rate = Column(Float, nullable=True)
    correlation_ratio = Column(Float, nullable=True)               # Observed / Baseline
    is_positive = Column(Boolean, default=True)
    evidence_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    @property
    def evidence(self):
        try: return json.loads(self.evidence_json)
        except: return {}

class ContentRecommendation(Base):
    __tablename__ = "content_recommendations"

    id = Column(String(64), primary_key=True, index=True)
    type = Column(String(64), nullable=False, index=True)          # BEST_FORMAT, BEST_PLATFORM, BEST_TOPIC, BEST_HOOK, BEST_DURATION, BEST_POSTING_WINDOW, CONTENT_GAP, UNDERPERFORMING_PATTERN, REPLICATION_OPPORTUNITY, EXPERIMENT_SUGGESTION
    scope = Column(String(32), default="ACCOUNT", index=True)
    platform = Column(String(32), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    recommendation_text = Column(Text, nullable=False)
    why_text = Column(Text, nullable=False)
    action_type = Column(String(64), nullable=True)                # CREATE_CLIP, CREATE_CAROUSEL, SCHEDULE_POST, CREATE_POST
    action_payload_json = Column(Text, default="{}")
    evidence_json = Column(Text, default="{}")
    sample_size = Column(Integer, default=0)
    confidence = Column(String(32), default="MEDIUM")              # HIGH, MEDIUM, LOW, INSUFFICIENT_DATA
    status = Column(String(32), default="ACTIVE", index=True)      # ACTIVE, DISMISSED, APPLIED
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    @property
    def evidence(self):
        try: return json.loads(self.evidence_json)
        except: return {}

    @property
    def action_payload(self):
        try: return json.loads(self.action_payload_json)
        except: return {}

class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    hypothesis = Column(Text, nullable=False)
    status = Column(String(32), default="DRAFT", index=True)     # DRAFT, READY, RUNNING, PAUSED, COMPLETED, CANCELLED, INSUFFICIENT_DATA
    scope = Column(String(64), nullable=True)                    # HOOK, CAPTION, THUMBNAIL, TITLE, DURATION, FORMAT, CAROUSEL_TEMPLATE, CTA, POSTING_WINDOW
    platform = Column(String(32), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    minimum_sample_size = Column(Integer, default=5)
    primary_metric = Column(String(64), default="engagement_rate")
    secondary_metrics_json = Column("secondary_metrics", Text, default="[]")              # JSON list of metrics
    confidence_level = Column(Float, default=0.95)
    winner_variant_id = Column(String(64), nullable=True)
    conclusion = Column(Text, nullable=True)
    created_by = Column(String(64), nullable=True)
    recommendation_id = Column(String(64), ForeignKey("content_recommendations.id", ondelete="SET NULL"), nullable=True)

    @property
    def secondary_metrics(self) -> List[str]:
        try: return json.loads(self.secondary_metrics_json or "[]")
        except: return []

    @secondary_metrics.setter
    def secondary_metrics(self, value):
        self.secondary_metrics_json = json.dumps(value or [])

    # Backwards compatibility fields for Phase 11
    title = Column(String(255), nullable=True)
    variable_tested = Column(String(128), nullable=True)
    control_baseline = Column(Float, nullable=True)
    success_metric = Column(String(64), default="engagement_rate")
    target_sample_size = Column(Integer, default=5)
    current_sample_size = Column(Integer, default=0)
    results_json = Column(Text, default="{}")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def results(self):
        try: return json.loads(self.results_json)
        except: return {}

    variants = relationship("ExperimentVariant", back_populates="experiment", cascade="all, delete-orphan", lazy="selectin")
    evaluation_results = relationship("ExperimentResult", back_populates="experiment", cascade="all, delete-orphan", lazy="selectin")

class ExperimentVariant(Base):
    __tablename__ = "experiment_variants"

    id = Column(String(64), primary_key=True, index=True)
    experiment_id = Column(String(64), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    content_id = Column(String(64), ForeignKey("contents.id", ondelete="SET NULL"), nullable=True, index=True)
    content_variant_id = Column(String(64), nullable=True)
    publication_id = Column(String(64), ForeignKey("publications.id", ondelete="SET NULL"), nullable=True, index=True)
    variant_type = Column(String(32), nullable=False)  # HOOK, CAPTION, THUMBNAIL, etc.
    role = Column(String(32), default="TREATMENT")     # CONTROL or TREATMENT
    created_at = Column(DateTime, default=datetime.utcnow)

    experiment = relationship("Experiment", back_populates="variants")
    publication = relationship("Publication", lazy="selectin")

class ExperimentResult(Base):
    __tablename__ = "experiment_results"

    id = Column(String(64), primary_key=True, index=True)
    experiment_id = Column(String(64), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    evaluated_at = Column(DateTime, default=datetime.utcnow, index=True)
    variant_id = Column(String(64), ForeignKey("experiment_variants.id", ondelete="CASCADE"), nullable=False, index=True)
    sample_size = Column(Integer, default=0)
    primary_metric = Column(String(64))
    metric_value = Column(Float, nullable=True)
    confidence_interval_low = Column(Float, nullable=True)
    confidence_interval_high = Column(Float, nullable=True)
    effect_size_absolute = Column(Float, nullable=True)
    effect_size_relative = Column(Float, nullable=True)
    p_value = Column(Float, nullable=True)
    statistical_significance = Column(Boolean, default=False)
    practical_significance = Column(Boolean, default=False)
    status = Column(String(32))

    experiment = relationship("Experiment", back_populates="evaluation_results")
    variant = relationship("ExperimentVariant", lazy="selectin")

class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, index=True)
    trigger_type = Column(String(64), nullable=False, index=True)
    scope = Column(String(64), nullable=True)
    conditions_json = Column("conditions", Text, default="[]")
    actions_json = Column("actions", Text, default="[]")
    cooldown_minutes = Column(Integer, default=60)
    max_runs_per_day = Column(Integer, default=5)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True, index=True)
    status = Column(String(32), default="ACTIVE", index=True)     # ACTIVE, PAUSED, ERROR, DISABLED
    created_by = Column(String(64), nullable=True)

    @property
    def conditions(self) -> List[Dict[str, Any]]:
        try: return json.loads(self.conditions_json or "[]")
        except: return []

    @conditions.setter
    def conditions(self, value):
        self.conditions_json = json.dumps(value or [])

    @property
    def actions(self) -> List[Dict[str, Any]]:
        try: return json.loads(self.actions_json or "[]")
        except: return []

    @actions.setter
    def actions(self, value):
        self.actions_json = json.dumps(value or [])

    executions = relationship("AutomationExecution", back_populates="rule", cascade="all, delete-orphan", lazy="selectin")

class AutomationExecution(Base):
    __tablename__ = "automation_executions"

    id = Column(String(64), primary_key=True, index=True)
    automation_id = Column(String(64), ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    trigger_event = Column(String(64), nullable=False)
    trigger_entity_id = Column(String(64), nullable=False)
    status = Column(String(32), default="QUEUED", index=True)     # QUEUED, RUNNING, SUCCEEDED, FAILED, SKIPPED
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    execution_key = Column(String(255), nullable=False, index=True)  # rule_id:entity_id
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    rule = relationship("AutomationRule", back_populates="executions")
    action_executions = relationship("AutomationActionExecution", back_populates="execution", cascade="all, delete-orphan", lazy="selectin")

class AutomationActionExecution(Base):
    __tablename__ = "automation_action_executions"

    id = Column(String(64), primary_key=True, index=True)
    execution_id = Column(String(64), ForeignKey("automation_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(64), nullable=False)
    status = Column(String(32), default="QUEUED", index=True)     # QUEUED, RUNNING, SUCCEEDED, FAILED, SKIPPED, BLOCKED, WAITING_APPROVAL
    job_id = Column(String(64), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    result_json = Column("result", Text, default="{}")
    error = Column(Text, nullable=True)

    @property
    def result(self) -> Dict[str, Any]:
        try: return json.loads(self.result_json or "{}")
        except: return {}

    @result.setter
    def result(self, value):
        self.result_json = json.dumps(value or {})

    execution = relationship("AutomationExecution", back_populates="action_executions")

class GovernancePolicy(Base):
    __tablename__ = "governance_policies"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, index=True)
    scope = Column(String(64), nullable=False, index=True)       # GLOBAL, PLATFORM, CONTENT_TYPE, AUTOMATION, WORKFLOW
    severity = Column(String(32), default="BLOCKING", index=True)  # INFO, WARNING, BLOCKING
    rules_json = Column("rules", Text, default="[]")
    policy_version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(64), nullable=True)

    @property
    def rules(self) -> List[Dict[str, Any]]:
        try: return json.loads(self.rules_json or "[]")
        except: return []

    @rules.setter
    def rules(self, value):
        self.rules_json = json.dumps(value or [])

class BrandProfile(Base):
    __tablename__ = "brand_profiles"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    tone = Column(String(128), default="professional")
    language = Column(String(32), default="en")
    allowed_topics_json = Column("allowed_topics", Text, default="[]")
    restricted_topics_json = Column("restricted_topics", Text, default="[]")
    preferred_ctas_json = Column("preferred_ctas", Text, default="[]")
    forbidden_terms_json = Column("forbidden_terms", Text, default="[]")
    required_terms_json = Column("required_terms", Text, default="[]")
    hashtag_rules_json = Column("hashtag_rules", Text, default="{}")
    mention_rules_json = Column("mention_rules", Text, default="{}")
    link_rules_json = Column("link_rules", Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(64), nullable=True)

    @property
    def allowed_topics(self) -> List[str]:
        try: return json.loads(self.allowed_topics_json or "[]")
        except: return []
    @allowed_topics.setter
    def allowed_topics(self, value): self.allowed_topics_json = json.dumps(value or [])

    @property
    def restricted_topics(self) -> List[str]:
        try: return json.loads(self.restricted_topics_json or "[]")
        except: return []
    @restricted_topics.setter
    def restricted_topics(self, value): self.restricted_topics_json = json.dumps(value or [])

    @property
    def preferred_ctas(self) -> List[str]:
        try: return json.loads(self.preferred_ctas_json or "[]")
        except: return []
    @preferred_ctas.setter
    def preferred_ctas(self, value): self.preferred_ctas_json = json.dumps(value or [])

    @property
    def forbidden_terms(self) -> List[str]:
        try: return json.loads(self.forbidden_terms_json or "[]")
        except: return []
    @forbidden_terms.setter
    def forbidden_terms(self, value): self.forbidden_terms_json = json.dumps(value or [])

    @property
    def required_terms(self) -> List[str]:
        try: return json.loads(self.required_terms_json or "[]")
        except: return []
    @required_terms.setter
    def required_terms(self, value): self.required_terms_json = json.dumps(value or [])

    @property
    def hashtag_rules(self) -> Dict[str, Any]:
        try: return json.loads(self.hashtag_rules_json or "{}")
        except: return {}
    @hashtag_rules.setter
    def hashtag_rules(self, value): self.hashtag_rules_json = json.dumps(value or {})

    @property
    def mention_rules(self) -> Dict[str, Any]:
        try: return json.loads(self.mention_rules_json or "{}")
        except: return {}
    @mention_rules.setter
    def mention_rules(self, value): self.mention_rules_json = json.dumps(value or {})

    @property
    def link_rules(self) -> Dict[str, Any]:
        try: return json.loads(self.link_rules_json or "{}")
        except: return {}
    @link_rules.setter
    def link_rules(self, value): self.link_rules_json = json.dumps(value or {})

class QualityCheck(Base):
    __tablename__ = "quality_checks"

    id = Column(String(64), primary_key=True, index=True)
    content_id = Column(String(64), ForeignKey("contents.id", ondelete="CASCADE"), nullable=True, index=True)
    variant_id = Column(String(64), nullable=True, index=True)
    publication_id = Column(String(64), ForeignKey("publications.id", ondelete="CASCADE"), nullable=True, index=True)
    check_type = Column(String(64), nullable=False, index=True)  # MEDIA_VALIDITY, BRAND_COMPLIANCE, etc.
    status = Column(String(32), default="PENDING", index=True)     # PENDING, RUNNING, PASSED, WARNING, FAILED, SKIPPED
    severity = Column(String(32), default="BLOCKING", index=True)  # INFO, WARNING, BLOCKING
    score = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    details_json = Column("details", Text, default="{}")
    policy_version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    @property
    def details(self) -> Dict[str, Any]:
        try: return json.loads(self.details_json or "{}")
        except: return {}
    @details.setter
    def details(self, value): self.details_json = json.dumps(value or {})

    override = relationship("GovernanceOverride", back_populates="quality_check", cascade="all, delete-orphan", uselist=False)

class ContentClaim(Base):
    __tablename__ = "content_claims"

    id = Column(String(64), primary_key=True, index=True)
    content_id = Column(String(64), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    source_reference = Column(Text, nullable=True)
    verification_status = Column(String(32), default="UNVERIFIED", index=True) # UNVERIFIED, SUPPORTED, CONTRADICTED, NOT_APPLICABLE
    severity = Column(String(32), default="WARNING")
    created_at = Column(DateTime, default=datetime.utcnow)

class GovernanceOverride(Base):
    __tablename__ = "governance_overrides"

    id = Column(String(64), primary_key=True, index=True)
    quality_check_id = Column(String(64), ForeignKey("quality_checks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), nullable=True)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    quality_check = relationship("QualityCheck", back_populates="override")

class GovernanceResult(Base):
    __tablename__ = "governance_results"

    id = Column(String(64), primary_key=True, index=True)
    content_id = Column(String(64), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), default="PASS", index=True) # PASS, PASS_WITH_WARNINGS, BLOCKED
    blocking_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    info_count = Column(Integer, default=0)
    evaluated_at = Column(DateTime, default=datetime.utcnow, index=True)
    policy_version = Column(Integer, default=1)

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(64), primary_key=True, index=True)
    type = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(32), default="INFO", index=True)
    read = Column(Boolean, default=False, index=True)
    entity_type = Column(String(64), nullable=True)
    entity_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class PluginConfiguration(Base):
    __tablename__ = "plugin_configurations"

    id = Column(String(64), primary_key=True, index=True)
    plugin_id = Column(String(128), nullable=False, unique=True, index=True)
    enabled = Column(Boolean, default=True, index=True)
    configuration_json = Column(Text, default="{}")
    health_status = Column(String(32), default="HEALTHY", index=True)
    permissions_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id = Column(String(64), primary_key=True, index=True)
    url = Column(String(512), nullable=False)
    events_json = Column(Text, default="[]") # List of subscribed event strings
    enabled = Column(Boolean, default=True, index=True)
    secret = Column(String(128), nullable=False) # HMAC signing secret
    last_success_at = Column(DateTime, nullable=True)
    last_failure_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    prefix = Column(String(16), nullable=False, index=True) # e.g. reflow_live_
    hashed_key = Column(String(255), nullable=False, unique=True, index=True)
    permissions_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)


class PluginInstallation(Base):
    __tablename__ = "plugin_installations"

    id = Column(String(64), primary_key=True, index=True)
    plugin_id = Column(String(128), unique=True, index=True, nullable=False)
    version = Column(String(32), nullable=False)
    enabled = Column(Boolean, default=True)
    source_type = Column(String(32), default="OFFICIAL")
    config_json = Column(Text, default="{}")
    health_status = Column(String(32), default="HEALTHY")
    installed_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PluginAuditLog(Base):
    __tablename__ = "plugin_audit_logs"

    id = Column(String(64), primary_key=True, index=True)
    plugin_id = Column(String(128), index=True, nullable=False)
    action = Column(String(64), nullable=False)
    details_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)



