export type ContentType = 'VIDEO' | 'IMAGE' | 'PDF' | 'TEXT' | 'CAROUSEL' | 'video' | 'image' | 'pdf' | 'text' | 'carousel';
export type ContentStatus = 'UPLOADING' | 'PROCESSING' | 'READY' | 'FAILED' | 'DRAFT' | 'draft' | 'processing' | 'scheduled' | 'published' | 'failed';

export interface ContentVariant {
  id: string;
  content_id: string;
  source_asset_id?: string;
  variant_type: string;  // THUMBNAIL, LANDSCAPE_16_9, VERTICAL_9_16, SQUARE_1_1, PORTRAIT_4_5, ORIGINAL
  storage_key: string;
  mime_type: string;
  file_size: number;
  width?: number;
  height?: number;
  duration?: number;
  fps?: number;
  codec?: string;
  status: string;
  created_at?: string;
}

export interface TranscriptSegment {
  sequence: number;
  start_time: number;
  end_time: number;
  text: string;
}

export interface Transcript {
  id: string;
  content_id: string;
  asset_id?: string;
  provider: string;
  language: string;
  text: string;
  duration?: number;
  status: string;
  created_at?: string;
  segments: TranscriptSegment[];
}

export interface ContentBrief {
  id: string;
  content_id: string;
  transcript_id?: string;
  title: string;
  summary: string;
  topics: string[];
  keywords: string[];
  audience: string;
  tone: string;
  key_points: string[];
  hooks: string[];
  quotes: string[];
  cta_suggestions: string[];
  provider: string;
  model: string;
  prompt_version: string;
  created_at?: string;
}

export interface GeneratedContent {
  id: string;
  content_id: string;
  brief_id?: string;
  platform: string;       // LINKEDIN, INSTAGRAM, X, YOUTUBE
  generation_type: string;
  status: string;
  payload: any;           // Platform specific payload
  provider: string;
  model: string;
  prompt_version: string;
  version: number;
  created_at?: string;
}

export interface SlideElementItem {
  id: string;
  slide_id: string;
  type: string;
  position_x: number;
  position_y: number;
  width: number;
  height: number;
  content: string;
  style: any;
  z_index: number;
}

export interface CarouselSlideItem {
  id: string;
  carousel_id: string;
  position: number;
  purpose: string;
  layout: string;
  headline: string;
  body: string;
  tag?: string;
  background: string;
  created_at?: string;
  updated_at?: string;
  elements?: SlideElementItem[];
}

export interface CarouselExportItem {
  id: string;
  carousel_id: string;
  carousel_version: number;
  format: string; // PNG, JPG, PDF
  storage_key: string;
  file_size: number;
  status: string;
  created_at?: string;
}

export interface CarouselItem {
  id: string;
  content_id?: string;
  title: string;
  status: string;
  aspect_ratio: string;
  template: string;
  slide_count: number;
  version: number;
  created_at?: string;
  updated_at?: string;
  slides: CarouselSlideItem[];
  exports?: CarouselExportItem[];
}

export interface CarouselListResponse {
  items: CarouselItem[];
  total: number;
  page: number;
  limit: number;
}

export interface Asset {
  id: string;
  content_id: string;
  original_filename: string;
  storage_key: string;
  mime_type: string;
  file_size: number;
  duration?: number;
  width?: number;
  height?: number;
  fps?: number;
  codec?: string;
  bitrate?: number;
  created_at?: string;
}

export interface CaptionCue {
  start_time: number;
  end_time: number;
  text: string;
  highlight_words: string[];
}

export interface ClipCaptionsData {
  clip_id: string;
  caption_style: string;
  caption_enabled: boolean;
  highlight_keywords: string[];
  cues: CaptionCue[];
  srt_content: string;
  vtt_content: string;
}

export interface ClipVariantItem {
  id: string;
  clip_id: string;
  variant_type: string;
  aspect_ratio: string;
  storage_key: string;
  mime_type: string;
  width?: number;
  height?: number;
  duration?: number;
  file_size: number;
  has_captions?: boolean;
  caption_style?: string;
  status: string;
  created_at?: string;
}

export interface ClipItem {
  id: string;
  content_id: string;
  source_asset_id?: string;
  title: string;
  description?: string;
  hook?: string;
  start_time: number;
  end_time: number;
  duration: number;
  status: string;
  score: number;
  quality_score?: number;
  reason?: string;
  source_transcript_segment_ids?: string[];
  transcript_excerpt?: string;
  thumbnail_path?: string;
  discovery_version?: string;
  caption_style?: string;
  caption_enabled?: boolean;
  highlight_keywords?: string[];
  caption_custom_settings?: any;
  created_at?: string;
  updated_at?: string;
  variants?: ClipVariantItem[];
}

export interface ClipListResponse {
  items: ClipItem[];
  total: number;
}

export interface ContentItem {
  id: string;
  title: string;
  content_type: string;
  type?: string;
  status: string;
  text_content?: string;
  thumbnail_path?: string;
  created_at?: string;
  assets?: Asset[];
  destinations?: string[];
  variants?: ContentVariant[];
  transcripts?: Transcript[];
  briefs?: ContentBrief[];
  generated_contents?: GeneratedContent[];
  carousels?: CarouselItem[];
  clips?: ClipItem[];
}

export interface ContentListResponse {
  items: ContentItem[];
  total: number;
  page: number;
  limit: number;
}

export interface SocialAccount {
  id: string;
  name: string;
  handle: string;
  connected: boolean;
  avatar?: string;
  capabilities: string[];
}

export interface CarouselSlide {
  id: string;
  title: string;
  subtitle?: string;
  body: string;
  tag?: string;
  image_url?: string;
}

export interface CarouselTheme {
  background: string;
  font_family: string;
  accent_color: string;
  text_color: string;
}

export interface CarouselDeck {
  id: string;
  title: string;
  theme: CarouselTheme;
  slides: CarouselSlide[];
}

export interface WorkflowNode {
  id: string;
  type: 'trigger' | 'ai_processing' | 'split' | 'output' | 'filter' | 'delay';
  label: string;
  platform?: string;
  position: { x: number; y: number };
}

export interface Workflow {
  id: string;
  name: string;
  active: boolean;
  description: string;
  trigger: string;
  nodes: WorkflowNode[];
}

export interface ScheduledPost {
  id: string;
  content_id: string;
  title: string;
  platform: string;
  format: string;
  scheduled_time: string;
  status: string;
}

export interface PublishingJob {
  id: string;
  content_id?: string;
  type?: string;
  content_title?: string;
  platform?: string;
  status: string;
  time?: string;
  retry_count?: number;
  attempts?: number;
  error?: string;
  created_at?: string;
}

export interface SystemLog {
  id: string;
  level: 'INFO' | 'WARN' | 'ERROR';
  timestamp: string;
  service: string;
  message: string;
}

export interface PlatformConnectionItem {
  id: string;
  platform: string;
  name: string;
  account_name: string;
  handle: string;
  external_account_id?: string;
  status: 'CONNECTED' | 'DISCONNECTED' | 'REAUTH_REQUIRED' | 'EXPIRED';
  avatar_url?: string;
  capabilities: string[];
  scopes: string[];
  token_expires_at?: string;
  created_at?: string;
  updated_at?: string;
}

export interface PublicationItem {
  id: string;
  content_id: string;
  variant_id?: string;
  platform_connection_id?: string;
  platform: string;
  status: 'DRAFT' | 'SCHEDULED' | 'QUEUED' | 'UPLOADING' | 'PUBLISHING' | 'PUBLISHED' | 'FAILED' | 'REAUTH_REQUIRED' | 'CANCELLED';
  title: string;
  description?: string;
  privacy: 'PRIVATE' | 'UNLISTED' | 'PUBLIC';
  tags: string[];
  external_post_id?: string;
  external_url?: string;
  error_code?: string;
  error_message?: string;
  attempt_count: number;
  scheduled_at?: string;
  timezone?: string;
  claimed_at?: string;
  claim_owner?: string;
  cancelled_at?: string;
  failed_at?: string;
  created_at?: string;
  updated_at?: string;
  published_at?: string;
}

export interface PublicationCreateData {
  content_id: string;
  variant_id?: string;
  platform_connection_id: string;
  title: string;
  description?: string;
  tags?: string[];
  privacy?: 'PRIVATE' | 'UNLISTED' | 'PUBLIC';
}

export interface PublicationDestinationData {
  platform_connection_id: string;
  title?: string;
  description?: string;
  privacy?: 'PRIVATE' | 'UNLISTED' | 'PUBLIC';
  tags?: string[];
}

export interface BatchPublicationCreateData {
  content_id: string;
  variant_id?: string;
  destinations: PublicationDestinationData[];
}

export interface BatchPublicationResponse {
  publications: PublicationItem[];
  queued_count: number;
}

// Phase 9: Scheduling & Calendar Interfaces
export interface SchedulePublicationCreateData {
  content_id: string;
  variant_id?: string;
  scheduled_time: string;
  timezone: string;
  destinations: PublicationDestinationData[];
}

export interface SchedulePublicationResponse {
  publications: PublicationItem[];
  scheduled_count: number;
  scheduled_at_utc: string;
  timezone: string;
}

export interface RescheduleData {
  scheduled_time: string;
  timezone?: string;
}

export interface CalendarEventItem {
  id: string;
  publication_id: string;
  content_id: string;
  content_title: string;
  content_type: string;
  thumbnail_path?: string | null;
  variant_id?: string | null;
  platform: string;
  platform_connection_id?: string | null;
  account_name?: string;
  handle?: string;
  status: string;
  title: string;
  description: string;
  privacy: string;
  scheduled_at: string;
  scheduled_at_local: string;
  timezone: string;
  published_at?: string | null;
  external_post_id?: string | null;
  external_url?: string | null;
  error_code?: string | null;
  error_message?: string | null;
}

export interface CalendarResponse {
  items: CalendarEventItem[];
  total: number;
  start_utc: string;
  end_utc: string;
  timezone: string;
}

// Phase 10: Analytics & Performance Intelligence Interfaces
export interface PostMetricSnapshot {
  id: string;
  publication_id: string;
  platform: string;
  external_post_id?: string | null;
  captured_at: string;
  views?: number | null;
  impressions?: number | null;
  reach?: number | null;
  likes?: number | null;
  comments?: number | null;
  shares?: number | null;
  saves?: number | null;
  clicks?: number | null;
  reposts?: number | null;
  replies?: number | null;
  engagements?: number | null;
  watch_time_seconds?: number | null;
  average_watch_time_seconds?: number | null;
  completion_rate?: number | null;
  followers_gained?: number | null;
  engagement_rate?: number | null;
  view_rate?: number | null;
  raw_metrics?: Record<string, any> | null;
}

export interface PublicationAnalytics {
  publication: PublicationItem;
  content_title: string;
  content_type: string;
  latest_snapshot?: PostMetricSnapshot | null;
  snapshot_count: number;
  snapshots: PostMetricSnapshot[];
  views_per_hour?: number | null;
  engagements_per_hour?: number | null;
  is_stale: boolean;
}

export interface AnalyticsOverview {
  total_publications: number;
  total_views?: number | null;
  total_impressions?: number | null;
  total_reach?: number | null;
  total_engagements?: number | null;
  average_engagement_rate?: number | null;
  average_views_per_publication?: number | null;
  period_comparison?: Record<string, number | null> | null;
  start_date: string;
  end_date: string;
  last_synced_at?: string | null;
}

export interface AnalyticsTimeseriesItem {
  date: string;
  views?: number | null;
  engagements?: number | null;
  publications_count: number;
}

export interface AnalyticsTimeseriesResponse {
  items: AnalyticsTimeseriesItem[];
  total_days: number;
}

export interface PlatformAnalyticsItem {
  platform: string;
  publication_count: number;
  total_views?: number | null;
  total_impressions?: number | null;
  total_engagements?: number | null;
  engagement_rate?: number | null;
  supports_analytics: boolean;
  supported_metrics: string[];
}

export interface ContentAnalyticsItem {
  content_id: string;
  title: string;
  content_type: string;
  thumbnail_path?: string | null;
  publication_count: number;
  platforms: string[];
  total_views?: number | null;
  total_engagements?: number | null;
  engagement_rate?: number | null;
  top_platform?: string | null;
  latest_published_at?: string | null;
}

// Phase 11: Content Intelligence & Recommendation Interfaces
export interface PerformanceInsight {
  id: string;
  type: string;
  scope: string;
  platform?: string | null;
  title: string;
  description: string;
  evidence: Record<string, any>;
  sample_size: number;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT_DATA';
  source_metric: string;
  baseline_value?: number | null;
  observed_value?: number | null;
  delta_pct?: number | null;
  created_at: string;
}

export interface ContentPattern {
  id: string;
  pattern_type: string;
  feature_name: string;
  feature_value: string;
  sample_size: number;
  median_views?: number | null;
  median_engagement_rate?: number | null;
  correlation_ratio?: number | null;
  is_positive: boolean;
  evidence: Record<string, any>;
  created_at: string;
}

export interface ContentRecommendation {
  id: string;
  type: string;
  scope: string;
  platform?: string | null;
  title: string;
  recommendation_text: string;
  why_text: string;
  action_type?: string | null;
  action_payload: Record<string, any>;
  evidence: Record<string, any>;
  sample_size: number;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT_DATA';
  status: 'ACTIVE' | 'DISMISSED' | 'APPLIED';
  created_at: string;
}

export interface Experiment {
  id: string;
  name: string;
  description?: string | null;
  hypothesis: string;
  status: 'DRAFT' | 'READY' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'CANCELLED' | 'INSUFFICIENT_DATA';
  scope: 'HOOK' | 'CAPTION' | 'THUMBNAIL' | 'TITLE' | 'DURATION' | 'FORMAT' | 'CAROUSEL_TEMPLATE' | 'CTA' | 'POSTING_WINDOW';
  platform?: string | null;
  created_at: string;
  started_at?: string | null;
  ended_at?: string | null;
  minimum_sample_size: number;
  primary_metric: string;
  secondary_metrics: string[];
  confidence_level: number;
  winner_variant_id?: string | null;
  conclusion?: string | null;
  created_by?: string | null;
  recommendation_id?: string | null;

  // Backwards compatibility fields for Phase 11
  title?: string | null;
  variable_tested?: string | null;
  success_metric?: string | null;
  target_sample_size?: number | null;
  current_sample_size?: number | null;
  control_baseline?: number | null;
}

export interface ExperimentVariant {
  id: string;
  experiment_id: string;
  name: string;
  description?: string | null;
  content_id: string;
  content_variant_id?: string | null;
  publication_id?: string | null;
  variant_type?: string | null;
  role: 'CONTROL' | 'TREATMENT';
  created_at: string;
}

export interface ExperimentResult {
  id: string;
  experiment_id: string;
  variant_id: string;
  sample_size: number;
  metric_value?: number | null;
  abs_effect_size?: number | null;
  rel_effect_size?: number | null;
  p_value?: number | null;
  statistical_significance: boolean;
  practical_significance: boolean;
  evaluated_at: string;
}

export interface ExperimentWarning {
  code: string;
  message: string;
}

export interface ExperimentDetailResponse {
  experiment: Experiment;
  variants: ExperimentVariant[];
  results: ExperimentResult[];
  warnings: ExperimentWarning[];
}

export interface TopicPerformanceItem {
  topic: string;
  sample_size: number;
  median_views?: number | null;
  median_engagement_rate?: number | null;
  best_post_title?: string | null;
  best_post_id?: string | null;
  performance_vs_baseline_pct?: number | null;
  confidence: string;
}

export interface HookPerformanceItem {
  hook_type: string;
  sample_size: number;
  median_views?: number | null;
  median_engagement_rate?: number | null;
  performance_vs_baseline_pct?: number | null;
  confidence: string;
}

export interface DurationPerformanceItem {
  bucket: string;
  sample_size: number;
  median_views?: number | null;
  median_engagement_rate?: number | null;
  performance_vs_baseline_pct?: number | null;
  confidence: string;
}

export interface PostingWindowItem {
  day_of_week: string;
  hour_bucket: string;
  sample_size: number;
  median_engagement_rate?: number | null;
  performance_vs_baseline_pct?: number | null;
  confidence: string;
}

export interface ContentGapItem {
  topic: string;
  existing_posts_count: number;
  missing_format: string;
  opportunity_reason: string;
  topic_median_engagement_rate?: number | null;
  action_type: string;
  action_payload: Record<string, any>;
}

export interface IntelligenceOverview {
  total_analyzed_posts: number;
  account_baseline_engagement_rate?: number | null;
  account_baseline_views?: number | null;
  is_sufficient_data: boolean;
  minimum_samples_required: number;
  last_analyzed_at?: string | null;
  is_stale: boolean;
  top_recommendations: ContentRecommendation[];
  key_insights: PerformanceInsight[];
  content_gaps: ContentGapItem[];
}

export interface IntelligenceRefreshResponse {
  status: string;
  job_id: string;
  message: string;
}

// Phase 13: Content Distribution & Automation Types
export interface AutomationRule {
  id: string;
  name: string;
  description?: string | null;
  enabled: boolean;
  trigger_type: string;
  scope?: string | null;
  conditions: any[];
  actions: any[];
  cooldown_minutes: number;
  max_runs_per_day: number;
  created_at: string;
  updated_at: string;
  last_run_at?: string | null;
  next_run_at?: string | null;
  status: string;
  created_by?: string | null;
}

export interface AutomationActionExecution {
  id: string;
  execution_id: string;
  action_type: string;
  status: string;
  job_id?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  result: Record<string, any>;
  error?: string | null;
}

export interface AutomationExecution {
  id: string;
  automation_id: string;
  trigger_event: string;
  trigger_entity_id: string;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
  execution_key: string;
  created_at: string;
  action_executions: AutomationActionExecution[];
}

export interface AutomationDetailResponse {
  rule: AutomationRule;
  executions: AutomationExecution[];
  metrics: {
    total_runs: number;
    success_rate: number;
    failed_runs: number;
    skipped_runs: number;
  };
}

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  message: string;
  severity: 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR';
  read: boolean;
  entity_type?: string;
  entity_id?: string;
  created_at: string;
}

export interface SearchResultItem {
  id: string;
  type: 'content' | 'clip' | 'carousel' | 'publication' | 'experiment' | 'automation';
  title: string;
  subtitle?: string;
  url: string;
  status?: string;
  created_at?: string;
}


