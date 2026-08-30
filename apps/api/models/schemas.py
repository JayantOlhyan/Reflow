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

# ------------------------------------------------------------------------------
# Phase 5 Intelligent Clip Engine Schemas
# ------------------------------------------------------------------------------

class ClipCandidateSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Punchy, descriptive clip title")
    start_time: float = Field(..., ge=0, description="Start timestamp in seconds")
    end_time: float = Field(..., gt=0, description="End timestamp in seconds")
    reason: str = Field(default="", description="Why this segment is engaging and high-value")
    hook: str = Field(default="", description="Opening statement or hook of the clip")
    score: float = Field(default=80.0, ge=0.0, le=100.0, description="Ranking quality score")
    source_segment_ids: List[str] = Field(default_factory=list, description="IDs of source transcript segments")

class ClipCandidateListSchema(BaseModel):
    candidates: List[ClipCandidateSchema] = Field(..., description="List of recommended clip candidate intervals")

class ClipVariantResponse(BaseModel):
    id: str
    clip_id: str
    variant_type: str
    aspect_ratio: str
    storage_key: str
    mime_type: str = "video/mp4"
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    file_size: int = 0
    has_captions: bool = False
    caption_style: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ClipResponse(BaseModel):
    id: str
    content_id: str
    source_asset_id: Optional[str] = None
    title: str
    description: Optional[str] = ""
    hook: Optional[str] = ""
    start_time: float
    end_time: float
    duration: float
    status: str
    score: float = 80.0
    reason: Optional[str] = ""
    source_transcript_segment_ids: List[str] = []
    transcript_excerpt: Optional[str] = ""
    thumbnail_path: Optional[str] = None
    discovery_version: str = "v1"
    caption_style: str = "BOLD_PUNCH"
    caption_enabled: bool = True
    highlight_keywords: List[str] = []
    caption_custom_settings: Dict[str, Any] = {}
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    variants: List[ClipVariantResponse] = []

    model_config = ConfigDict(from_attributes=True)

class ClipListResponse(BaseModel):
    items: List[ClipResponse]
    total: int

class ClipDiscoveryRequest(BaseModel):
    min_duration: Optional[float] = 15.0
    max_duration: Optional[float] = 90.0
    target_count: Optional[int] = 5
    force_refresh: Optional[bool] = False

class ClipUpdateRequest(BaseModel):
    title: Optional[str] = None
    hook: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    caption_style: Optional[str] = None
    caption_enabled: Optional[bool] = None
    highlight_keywords: Optional[List[str]] = None

class ClipGenerateRequest(BaseModel):
    aspect_ratios: List[str] = Field(default=["9:16"])
    include_thumbnail: bool = True
    burn_captions: bool = False
    caption_style: Optional[str] = None

# Phase 6 Caption Schemas
class CaptionCueSchema(BaseModel):
    start_time: float
    end_time: float
    text: str
    highlight_words: List[str] = []

class ClipCaptionsResponse(BaseModel):
    clip_id: str
    caption_style: str
    caption_enabled: bool
    highlight_keywords: List[str] = []
    cues: List[CaptionCueSchema] = []
    srt_content: str = ""
    vtt_content: str = ""

class ClipCaptionsUpdateRequest(BaseModel):
    caption_style: Optional[str] = None
    caption_enabled: Optional[bool] = None
    highlight_keywords: Optional[List[str]] = None
    custom_settings: Optional[Dict[str, Any]] = None

class ClipCaptionRenderRequest(BaseModel):
    aspect_ratios: List[str] = Field(default=["9:16"])
    caption_style: Optional[str] = None
    highlight_keywords: Optional[List[str]] = None

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
    clips: List[ClipResponse] = []

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

# Phase 7 Platform Connections & Publishing Schemas
class PlatformConnectionResponse(BaseModel):
    id: str
    platform: str
    name: str
    account_name: Optional[str] = ""
    handle: Optional[str] = ""
    external_account_id: Optional[str] = None
    status: str = "CONNECTED"
    avatar_url: Optional[str] = ""
    capabilities: List[str] = []
    scopes: List[str] = []
    token_expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class PlatformConnectionListResponse(BaseModel):
    items: List[PlatformConnectionResponse]
    total: int

class OAuthStartResponse(BaseModel):
    platform: str
    authorization_url: str
    state: str

class PublicationCreateRequest(BaseModel):
    content_id: str
    variant_id: Optional[str] = None
    platform_connection_id: str
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = ""
    tags: List[str] = Field(default_factory=list)
    privacy: str = Field(default="PRIVATE", description="PRIVATE | UNLISTED | PUBLIC")

class PublicationResponse(BaseModel):
    id: str
    content_id: str
    variant_id: Optional[str] = None
    platform_connection_id: Optional[str] = None
    platform: str
    status: str
    title: str
    description: Optional[str] = ""
    privacy: str = "PRIVATE"
    tags: List[str] = []
    external_post_id: Optional[str] = None
    external_url: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    attempt_count: int = 0
    
    # Phase 9: Scheduling
    scheduled_at: Optional[datetime] = None
    timezone: Optional[str] = None
    claimed_at: Optional[datetime] = None
    claim_owner: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class PublicationListResponse(BaseModel):
    items: List[PublicationResponse]
    total: int

class PublicationDestinationItem(BaseModel):
    platform_connection_id: str
    title: Optional[str] = ""
    description: Optional[str] = ""
    privacy: Optional[str] = "PRIVATE"
    tags: Optional[List[str]] = []

class BatchPublicationCreateRequest(BaseModel):
    content_id: str
    variant_id: Optional[str] = None
    destinations: List[PublicationDestinationItem] = Field(..., min_items=1)

class BatchPublicationResponse(BaseModel):
    publications: List[PublicationResponse]
    queued_count: int

# Phase 9: Scheduling & Calendar Schemas
class ScheduleDestinationItem(BaseModel):
    platform_connection_id: str
    title: Optional[str] = ""
    description: Optional[str] = ""
    privacy: Optional[str] = "PRIVATE"
    tags: Optional[List[str]] = []

class SchedulePublicationCreateRequest(BaseModel):
    content_id: str
    variant_id: Optional[str] = None
    scheduled_time: str = Field(..., description="ISO 8601 string in local time, e.g. 2026-09-10T14:30:00")
    timezone: str = Field(default="UTC", description="IANA timezone name, e.g. 'Asia/Kolkata' or 'America/New_York'")
    destinations: List[ScheduleDestinationItem] = Field(..., min_items=1)

class SchedulePublicationResponse(BaseModel):
    publications: List[PublicationResponse]
    scheduled_count: int
    scheduled_at_utc: datetime
    timezone: str

class RescheduleRequest(BaseModel):
    scheduled_time: str = Field(..., description="ISO 8601 string in local time, e.g. 2026-09-10T15:30:00")
    timezone: Optional[str] = Field(default=None, description="IANA timezone name")

class CalendarEventItem(BaseModel):
    id: str
    publication_id: str
    content_id: str
    content_title: str
    content_type: str
    thumbnail_path: Optional[str] = None
    variant_id: Optional[str] = None
    platform: str
    platform_connection_id: Optional[str] = None
    account_name: Optional[str] = ""
    handle: Optional[str] = ""
    status: str
    title: str
    description: str
    privacy: str
    scheduled_at: datetime
    scheduled_at_local: str
    timezone: str
    published_at: Optional[datetime] = None
    external_post_id: Optional[str] = None
    external_url: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None

class CalendarResponse(BaseModel):
    items: List[CalendarEventItem]
    total: int
    start_utc: datetime
    end_utc: datetime
    timezone: str

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

# ------------------------------------------------------------------------------
# Phase 10: Real Analytics & Performance Intelligence Schemas
# ------------------------------------------------------------------------------

class PostMetricSnapshotResponse(BaseModel):
    id: str
    publication_id: str
    platform: str
    external_post_id: Optional[str] = None
    captured_at: datetime
    views: Optional[int] = None
    impressions: Optional[int] = None
    reach: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    saves: Optional[int] = None
    clicks: Optional[int] = None
    reposts: Optional[int] = None
    replies: Optional[int] = None
    engagements: Optional[int] = None
    watch_time_seconds: Optional[float] = None
    average_watch_time_seconds: Optional[float] = None
    completion_rate: Optional[float] = None
    followers_gained: Optional[int] = None
    engagement_rate: Optional[float] = None
    view_rate: Optional[float] = None
    raw_metrics: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class PublicationAnalyticsResponse(BaseModel):
    publication: PublicationResponse
    content_title: str
    content_type: str
    latest_snapshot: Optional[PostMetricSnapshotResponse] = None
    snapshot_count: int = 0
    snapshots: List[PostMetricSnapshotResponse] = []
    views_per_hour: Optional[float] = None
    engagements_per_hour: Optional[float] = None
    is_stale: bool = False

class AnalyticsOverviewResponse(BaseModel):
    total_publications: int
    total_views: Optional[int] = None
    total_impressions: Optional[int] = None
    total_reach: Optional[int] = None
    total_engagements: Optional[int] = None
    average_engagement_rate: Optional[float] = None
    average_views_per_publication: Optional[float] = None
    period_comparison: Optional[Dict[str, Any]] = None
    start_date: datetime
    end_date: datetime
    last_synced_at: Optional[datetime] = None

class AnalyticsTimeseriesItem(BaseModel):
    date: str
    views: Optional[int] = None
    engagements: Optional[int] = None
    publications_count: int = 0

class AnalyticsTimeseriesResponse(BaseModel):
    items: List[AnalyticsTimeseriesItem]
    total_days: int

class PlatformAnalyticsItem(BaseModel):
    platform: str
    publication_count: int
    total_views: Optional[int] = None
    total_impressions: Optional[int] = None
    total_engagements: Optional[int] = None
    engagement_rate: Optional[float] = None
    supports_analytics: bool = False
    supported_metrics: List[str] = []

class ContentAnalyticsItem(BaseModel):
    content_id: str
    title: str
    content_type: str
    thumbnail_path: Optional[str] = None
    publication_count: int
    platforms: List[str]
    total_views: Optional[int] = None
    total_engagements: Optional[int] = None
    engagement_rate: Optional[float] = None
    top_platform: Optional[str] = None
    latest_published_at: Optional[datetime] = None

class AnalyticsBackfillRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    platform: Optional[str] = None
    limit: int = 50

class AnalyticsBackfillResponse(BaseModel):
    queued_count: int
    message: str

# ------------------------------------------------------------------------------
# Phase 11: Real Content Intelligence & Recommendation Schemas
# ------------------------------------------------------------------------------

class PerformanceInsightResponse(BaseModel):
    id: str
    type: str
    scope: str
    platform: Optional[str] = None
    title: str
    description: str
    evidence: Dict[str, Any] = {}
    sample_size: int
    confidence: str
    source_metric: str
    baseline_value: Optional[float] = None
    observed_value: Optional[float] = None
    delta_pct: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ContentPatternResponse(BaseModel):
    id: str
    pattern_type: str
    feature_name: str
    feature_value: str
    sample_size: int
    median_views: Optional[float] = None
    median_engagement_rate: Optional[float] = None
    correlation_ratio: Optional[float] = None
    is_positive: bool
    evidence: Dict[str, Any] = {}
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ContentRecommendationResponse(BaseModel):
    id: str
    type: str
    scope: str
    platform: Optional[str] = None
    title: str
    recommendation_text: str
    why_text: str
    action_type: Optional[str] = None
    action_payload: Dict[str, Any] = {}
    evidence: Dict[str, Any] = {}
    sample_size: int
    confidence: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ExperimentResponse(BaseModel):
    id: str
    title: str
    hypothesis: str
    variable_tested: str
    control_baseline: Optional[float] = None
    success_metric: str
    target_sample_size: int
    current_sample_size: int
    status: str
    results: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TopicPerformanceItem(BaseModel):
    topic: str
    sample_size: int
    median_views: Optional[float] = None
    median_engagement_rate: Optional[float] = None
    best_post_title: Optional[str] = None
    best_post_id: Optional[str] = None
    performance_vs_baseline_pct: Optional[float] = None
    confidence: str

class HookPerformanceItem(BaseModel):
    hook_type: str
    sample_size: int
    median_views: Optional[float] = None
    median_engagement_rate: Optional[float] = None
    performance_vs_baseline_pct: Optional[float] = None
    confidence: str

class DurationPerformanceItem(BaseModel):
    bucket: str
    sample_size: int
    median_views: Optional[float] = None
    median_engagement_rate: Optional[float] = None
    performance_vs_baseline_pct: Optional[float] = None
    confidence: str

class PostingWindowItem(BaseModel):
    day_of_week: str
    hour_bucket: str
    sample_size: int
    median_engagement_rate: Optional[float] = None
    performance_vs_baseline_pct: Optional[float] = None
    confidence: str

class ContentGapItem(BaseModel):
    topic: str
    existing_posts_count: int
    missing_format: str
    opportunity_reason: str
    topic_median_engagement_rate: Optional[float] = None
    action_type: str
    action_payload: Dict[str, Any] = {}

class IntelligenceOverviewResponse(BaseModel):
    total_analyzed_posts: int
    account_baseline_engagement_rate: Optional[float] = None
    account_baseline_views: Optional[float] = None
    is_sufficient_data: bool
    minimum_samples_required: int
    last_analyzed_at: Optional[datetime] = None
    is_stale: bool = False
    top_recommendations: List[ContentRecommendationResponse] = []
    key_insights: List[PerformanceInsightResponse] = []
    content_gaps: List[ContentGapItem] = []

class IntelligenceRefreshResponse(BaseModel):
    status: str
    job_id: str
    message: str

class AIInsightPayloadSchema(BaseModel):
    claim: str
    evidence: Dict[str, Any]
    confidence: str
    recommendation: str

# ------------------------------------------------------------------------------
# Phase 12: Content Experimentation Schemas
# ------------------------------------------------------------------------------

class ExperimentVariantSchema(BaseModel):
    id: str
    experiment_id: str
    name: str
    description: Optional[str] = None
    content_id: Optional[str] = None
    content_variant_id: Optional[str] = None
    publication_id: Optional[str] = None
    variant_type: str
    role: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ExperimentResultResponse(BaseModel):
    id: str
    experiment_id: str
    evaluated_at: Optional[datetime] = None
    variant_id: str
    sample_size: int
    primary_metric: str
    metric_value: Optional[float] = None
    confidence_interval_low: Optional[float] = None
    confidence_interval_high: Optional[float] = None
    effect_size_absolute: Optional[float] = None
    effect_size_relative: Optional[float] = None
    p_value: Optional[float] = None
    statistical_significance: bool = False
    practical_significance: bool = False
    status: str

    model_config = ConfigDict(from_attributes=True)

class ExperimentWarningSchema(BaseModel):
    code: str
    message: str

class ExperimentResponse(BaseModel):
    id: str
    name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    hypothesis: str
    status: str
    scope: Optional[str] = None
    platform: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    minimum_sample_size: int
    primary_metric: str
    secondary_metrics: List[str] = []
    confidence_level: float
    winner_variant_id: Optional[str] = None
    conclusion: Optional[str] = None
    created_by: Optional[str] = None
    recommendation_id: Optional[str] = None
    current_sample_size: int = 0

    model_config = ConfigDict(from_attributes=True)

class ExperimentDetailResponse(BaseModel):
    experiment: ExperimentResponse
    variants: List[ExperimentVariantSchema] = []
    results: List[ExperimentResultResponse] = []
    warnings: List[ExperimentWarningSchema] = []

class ExperimentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    hypothesis: str = Field(..., min_length=5)
    platform: str
    primary_metric: str = "engagement_rate"
    secondary_metrics: Optional[List[str]] = []
    minimum_sample_size: Optional[int] = 5
    confidence_level: Optional[float] = 0.95
    scope: str  # HOOK, CAPTION, THUMBNAIL, etc.
    recommendation_id: Optional[str] = None
    control_content_id: str
    control_variant_id: Optional[str] = None
    control_publication_id: Optional[str] = None
    treatment_content_id: str
    treatment_variant_id: Optional[str] = None
    treatment_publication_id: Optional[str] = None

# Phase 13: Content Distribution & Automation Engine Schemas
class AutomationRuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    enabled: bool = True
    trigger_type: str
    scope: Optional[str] = None
    conditions: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []
    cooldown_minutes: Optional[int] = 60
    max_runs_per_day: Optional[int] = 5

class AutomationRuleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    enabled: bool
    trigger_type: str
    scope: Optional[str] = None
    conditions: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []
    cooldown_minutes: int
    max_runs_per_day: int
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    status: str
    created_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class AutomationActionExecutionResponse(BaseModel):
    id: str
    execution_id: str
    action_type: str
    status: str
    job_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Dict[str, Any] = {}
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class AutomationExecutionResponse(BaseModel):
    id: str
    automation_id: str
    trigger_event: str
    trigger_entity_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    execution_key: str
    created_at: datetime
    action_executions: List[AutomationActionExecutionResponse] = []

    model_config = ConfigDict(from_attributes=True)

class AutomationDetailResponse(BaseModel):
    rule: AutomationRuleResponse
    executions: List[AutomationExecutionResponse] = []
    metrics: Dict[str, Any] = {}


# ------------------------------------------------------------------------------
# Phase 14 Governance & Quality Control Schemas
# ------------------------------------------------------------------------------

class GovernanceRuleSchema(BaseModel):
    name: str
    type: str  # e.g., "codec", "aspect_ratio", "forbidden_term", "max_length"
    params: Dict[str, Any] = {}

class GovernancePolicyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    scope: str = "GLOBAL"  # GLOBAL, PLATFORM, CONTENT_TYPE, AUTOMATION, WORKFLOW
    severity: str = "BLOCKING"  # INFO, WARNING, BLOCKING
    rules: List[GovernanceRuleSchema] = []
    enabled: Optional[bool] = True

class GovernancePolicyUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[str] = None
    severity: Optional[str] = None
    rules: Optional[List[GovernanceRuleSchema]] = None
    enabled: Optional[bool] = None

class GovernancePolicyResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    enabled: bool
    scope: str
    severity: str
    rules: List[Dict[str, Any]] = []
    policy_version: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class BrandProfileCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    tone: Optional[str] = "professional"
    language: Optional[str] = "en"
    allowed_topics: Optional[List[str]] = []
    restricted_topics: Optional[List[str]] = []
    preferred_ctas: Optional[List[str]] = []
    forbidden_terms: Optional[List[str]] = []
    required_terms: Optional[List[str]] = []
    hashtag_rules: Optional[Dict[str, Any]] = {}
    mention_rules: Optional[Dict[str, Any]] = {}
    link_rules: Optional[Dict[str, Any]] = {}

class BrandProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tone: Optional[str] = None
    language: Optional[str] = None
    allowed_topics: Optional[List[str]] = None
    restricted_topics: Optional[List[str]] = None
    preferred_ctas: Optional[List[str]] = None
    forbidden_terms: Optional[List[str]] = None
    required_terms: Optional[List[str]] = None
    hashtag_rules: Optional[Dict[str, Any]] = None
    mention_rules: Optional[Dict[str, Any]] = None
    link_rules: Optional[Dict[str, Any]] = None

class BrandProfileResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    tone: str
    language: str
    allowed_topics: List[str] = []
    restricted_topics: List[str] = []
    preferred_ctas: List[str] = []
    forbidden_terms: List[str] = []
    required_terms: List[str] = []
    hashtag_rules: Dict[str, Any] = {}
    mention_rules: Dict[str, Any] = {}
    link_rules: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class GovernanceOverrideResponse(BaseModel):
    id: str
    quality_check_id: str
    user_id: Optional[str] = None
    reason: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class QualityCheckResponse(BaseModel):
    id: str
    content_id: Optional[str] = None
    variant_id: Optional[str] = None
    publication_id: Optional[str] = None
    check_type: str
    status: str
    severity: str
    score: Optional[float] = None
    message: Optional[str] = None
    details: Dict[str, Any] = {}
    policy_version: int
    created_at: datetime
    override: Optional[GovernanceOverrideResponse] = None

    model_config = ConfigDict(from_attributes=True)

class ContentClaimResponse(BaseModel):
    id: str
    content_id: str
    text: str
    source_reference: Optional[str] = None
    verification_status: str
    severity: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class GovernanceOverrideRequest(BaseModel):
    reason: str = Field(..., min_length=4)

class GovernanceResultResponse(BaseModel):
    content_id: str
    status: str
    blocking_count: int
    warning_count: int
    info_count: int
    evaluated_at: datetime
    policy_version: int

    model_config = ConfigDict(from_attributes=True)

