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
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ContentVariantSchema(BaseModel):
    platform: str
    format: str
    status: str = "DRAFT"
    storage_path: Optional[str] = None
    copy_text: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ContentResponse(BaseModel):
    id: str
    title: str
    content_type: str  # VIDEO, IMAGE, PDF, TEXT
    status: str        # UPLOADING, READY, FAILED
    text_content: Optional[str] = None
    thumbnail_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    assets: List[AssetResponse] = []
    variants: List[ContentVariantSchema] = []

    model_config = ConfigDict(from_attributes=True)

class ContentListResponse(BaseModel):
    items: List[ContentResponse]
    total: int
    page: int
    limit: int

class TextContentCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    text: str = Field(..., min_length=1)

class ContentCreateRequest(BaseModel):
    title: str
    type: str = "VIDEO"
    text_content: Optional[str] = None

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

class CarouselSlide(BaseModel):
    id: str
    title: str
    subtitle: Optional[str] = ""
    body: str
    tag: Optional[str] = ""
    image_url: Optional[str] = None

class CarouselTheme(BaseModel):
    background: str = "#0F172A"
    font_family: str = "Inter"
    accent_color: str = "#6366F1"
    text_color: str = "#FFFFFF"

class CarouselDeck(BaseModel):
    id: str
    title: str
    theme: CarouselTheme = Field(default_factory=CarouselTheme)
    slides: List[CarouselSlide] = []

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

class JobSchema(BaseModel):
    id: str
    type: str
    status: str
    attempts: int = 0
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class HealthComponentStatus(BaseModel):
    status: str
    details: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    components: Dict[str, HealthComponentStatus]
