from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

class ApiResponse(BaseModel):
    status: str = "success"
    message: Optional[str] = None
    data: Optional[Any] = None

class AssetResponse(BaseModel):
    id: str
    content_id: str
    original_filename: str
    storage_key: str
    mime_type: str
    file_size: int
    duration: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[int] = None
    codec: Optional[str] = None
    bitrate: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ContentVariantResponse(BaseModel):
    id: str
    content_id: str
    source_asset_id: Optional[str] = None
    variant_type: str
    storage_key: str
    mime_type: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None
    fps: Optional[int] = None
    codec: Optional[str] = None
    status: str = "READY"
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class TranscriptSegmentSchema(BaseModel):
    sequence: int
    start_time: float
    end_time: float
    text: str

    model_config = ConfigDict(from_attributes=True)

class TranscriptResponse(BaseModel):
    id: str
    content_id: str
    asset_id: Optional[str] = None
    provider: str
    language: str
    text: str
    duration: Optional[float] = None
    status: str
    created_at: Optional[datetime] = None
    segments: List[TranscriptSegmentSchema] = []

    model_config = ConfigDict(from_attributes=True)

class ContentBriefSchema(BaseModel):
    title: str = Field(..., description="High-impact title synthesizing core thesis")
    summary: str = Field(..., description="Comprehensive summary of content")
    topics: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    audience: str = Field(default="Creators & Developers")
    tone: str = Field(default="Professional & Engaging")
    key_points: List[str] = Field(default_factory=list)
    hooks: List[str] = Field(default_factory=list)
    quotes: List[str] = Field(default_factory=list)
    cta_suggestions: List[str] = Field(default_factory=list)

class ContentBriefResponse(BaseModel):
    id: str
    content_id: str
    transcript_id: Optional[str] = None
    title: str
    summary: str
    topics: List[str] = []
    keywords: List[str] = []
    audience: str = "General Audience"
    tone: str = "Professional"
    key_points: List[str] = []
    hooks: List[str] = []
    quotes: List[str] = []
    cta_suggestions: List[str] = []
    provider: str
    model: str
    prompt_version: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class LinkedInPostSchema(BaseModel):
    title: str
    hook: str
    body: str
    key_takeaway: str
    call_to_action: str
    hashtags: List[str] = []

class InstagramPostSchema(BaseModel):
    hook: str
    caption: str
    call_to_action: str
    hashtags: List[str] = []

class XPostSchema(BaseModel):
    post_text: str = Field(..., max_length=280)
    character_count: int

class XThreadPostSchema(BaseModel):
    thread_title: str
    posts: List[str] = Field(..., min_items=1)
    total_posts: int

class YouTubeChapterSchema(BaseModel):
    timestamp: str
    title: str

class YouTubePostSchema(BaseModel):
    title: str = Field(..., max_length=100)
    description: str
    tags: List[str] = []
    chapters: List[YouTubeChapterSchema] = []

class GeneratedContentResponse(BaseModel):
    id: str
    content_id: str
    brief_id: Optional[str] = None
    platform: str
    generation_type: str
    status: str
    payload: Dict[str, Any] = {}
    provider: str
    model: str
    prompt_version: str
    version: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# ------------------------------------------------------------------------------
# Phase 4 Carousel Engine Schemas
# ------------------------------------------------------------------------------

class SlideElementSchema(BaseModel):
    id: Optional[str] = None
    type: str = "TEXT"  # TEXT, IMAGE, SHAPE, ICON
    position_x: float = 0.0
    position_y: float = 0.0
    width: float = 100.0
    height: float = 100.0
    content: str = ""
    style: Dict[str, Any] = {}
    z_index: int = 1

    model_config = ConfigDict(from_attributes=True)

class CarouselSlideResponse(BaseModel):
    id: str
    carousel_id: str
    position: int
    purpose: str
    layout: str
    headline: str
    body: str
    tag: Optional[str] = ""
    background: str = "#0F172A"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    elements: List[SlideElementSchema] = []

    model_config = ConfigDict(from_attributes=True)

class CarouselExportResponse(BaseModel):
    id: str
    carousel_id: str
    carousel_version: int
    format: str  # PNG, JPG, PDF
    storage_key: str
    file_size: int
    status: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class CarouselResponse(BaseModel):
    id: str
    content_id: Optional[str] = None
    title: str
    status: str
    aspect_ratio: str = "1:1"
    template: str = "MINIMAL"
    slide_count: int = 0
    version: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    slides: List[CarouselSlideResponse] = []
    exports: List[CarouselExportResponse] = []

    model_config = ConfigDict(from_attributes=True)

class CarouselListResponse(BaseModel):
    items: List[CarouselResponse]
    total: int
    page: int
    limit: int

class CarouselCreateRequest(BaseModel):
    content_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=255)
    template: Optional[str] = "MINIMAL"
    aspect_ratio: Optional[str] = "1:1"

class CarouselUpdateRequest(BaseModel):
    title: Optional[str] = None
    template: Optional[str] = None
    aspect_ratio: Optional[str] = None

class SlideCreateRequest(BaseModel):
    position: Optional[int] = None
    purpose: str = "KEY_POINT"
    layout: str = "TITLE_BODY"
    headline: str = Field(..., min_length=1)
    body: str = ""
    tag: Optional[str] = ""
    background: Optional[str] = "#0F172A"

class SlideUpdateRequest(BaseModel):
    purpose: Optional[str] = None
    layout: Optional[str] = None
    headline: Optional[str] = None
    body: Optional[str] = None
    tag: Optional[str] = None
    background: Optional[str] = None

class SlideReorderRequest(BaseModel):
    slide_ids: List[str] = Field(..., min_items=1)

# AI Carousel Plan Schemas
class CarouselPlanSlideSchema(BaseModel):
    position: int
    purpose: str = Field(..., description="HOOK, PROBLEM, INSIGHT, KEY_POINT, EXAMPLE, STATISTIC, QUOTE, FRAMEWORK, SUMMARY, CTA")
    layout: str = Field(default="TITLE_BODY", description="TITLE, TITLE_BODY, FULL_IMAGE, QUOTE, STATISTIC, TWO_COLUMN, FRAMEWORK, CTA")
    headline: str = Field(..., description="Concise slide title or punchline")
    body: str = Field(..., description="Core slide insight or narrative copy")
    tag: Optional[str] = Field(default="INSIGHT", description="Category pill or theme tag")

class CarouselPlanSchema(BaseModel):
    title: str = Field(..., description="Deck title")
    template: str = Field(default="MINIMAL")
    slides: List[CarouselPlanSlideSchema] = Field(..., min_items=4, max_items=12)

class CarouselGenerateRequest(BaseModel):
    topic_or_content_id: Optional[str] = None
    slide_count: int = Field(default=5, ge=4, le=12)
    template: str = Field(default="MINIMAL")
    tone: Optional[str] = "informative"
    custom_prompt: Optional[str] = None

class ContentResponse(BaseModel):
    id: str
    title: str
    content_type: str
    status: str
    text_content: Optional[str] = None
    thumbnail_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    assets: List[AssetResponse] = []
    variants: List[ContentVariantResponse] = []
    transcripts: List[TranscriptResponse] = []
    briefs: List[ContentBriefResponse] = []
    generated_contents: List[GeneratedContentResponse] = []
    carousels: List[CarouselResponse] = []

    model_config = ConfigDict(from_attributes=True)

class ContentListResponse(BaseModel):
    items: List[ContentResponse]
    total: int
    page: int
    limit: int

class TextContentCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    text: str = Field(..., min_length=1)

class AIGenerateRequest(BaseModel):
    platforms: List[str] = Field(default=["LINKEDIN", "INSTAGRAM", "X", "YOUTUBE"])
    tone: Optional[str] = Field(default="professional")
    custom_instructions: Optional[str] = None

class RepurposeRequest(BaseModel):
    content_id: str
    target_format: str = "9:16"
    destinations: List[str] = ["instagram", "youtube", "linkedin", "x", "tiktok"]
    ai_options: Dict[str, bool] = Field(default_factory=lambda: {
        "caption": True,
        "title": True,
        "description": True,
        "hashtags": True,
        "subtitles": False,
        "find_clips": False
    })
    custom_prompt: Optional[str] = None

class AICarouselPrompt(BaseModel):
    topic: str
    slide_count: int = 5
    tone: str = "informative"
    audience: str = "creators & developers"

class SchedulePostRequest(BaseModel):
    content_id: str
    title: str
    platform: str
    format: str
    scheduled_time: str

class PlatformConnectionSchema(BaseModel):
    id: str
    name: str
    handle: str = ""
    connected: bool = False
    avatar_url: Optional[str] = ""
    capabilities: List[str] = []

    model_config = ConfigDict(from_attributes=True)

class PlatformConnectionUpdate(BaseModel):
    id: str
    connected: bool
    handle: Optional[str] = ""

class JobResponse(BaseModel):
    id: str
    content_id: Optional[str] = None
    asset_id: Optional[str] = None
    type: str
    status: str
    attempts: int = 0
    max_attempts: int = 3
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class HealthComponentStatus(BaseModel):
    status: str
    details: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    components: Dict[str, HealthComponentStatus]
