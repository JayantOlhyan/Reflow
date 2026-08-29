import json
from datetime import datetime
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

class PlatformConnection(Base):
    __tablename__ = "platform_connections"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(64), nullable=False)
    handle = Column(String(128), default="")
    connected = Column(Boolean, default=False)
    avatar_url = Column(String(512), default="")
    capabilities_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def capabilities(self):
        try: return json.loads(self.capabilities_json)
        except: return []

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
