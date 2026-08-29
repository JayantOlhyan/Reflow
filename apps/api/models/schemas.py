from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ContentItem(BaseModel):
    id: str
    title: str
    type: str  # video, carousel, image, text
    source: Optional[str] = ""
    thumbnail: Optional[str] = ""
    duration: Optional[int] = None
    slide_count: Optional[int] = None
    dimensions: Optional[str] = None
    status: str = "draft"  # draft, scheduled, published, failed, processing
    created_at: str
    destinations: List[str] = []
    variants: List[Dict[str, Any]] = []

class RepurposeRequest(BaseModel):
    content_id: str
    target_format: str  # 16:9, 9:16, 1:1, 4:5
    destinations: List[str]  # ['youtube', 'instagram', 'tiktok', 'linkedin', 'x', 'facebook']
    ai_options: Dict[str, bool] = {
        "caption": True,
        "title": True,
        "description": True,
        "hashtags": True,
        "subtitles": False,
        "find_clips": False
    }
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

class CarouselData(BaseModel):
    id: str
    title: str
    theme: CarouselTheme
    slides: List[CarouselSlide]

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

class PlatformConnectionUpdate(BaseModel):
    id: str
    connected: bool
    handle: Optional[str] = ""

class WorkflowModel(BaseModel):
    id: str
    name: str
    active: bool = True
    description: str
    trigger: str
    nodes: List[Dict[str, Any]]
