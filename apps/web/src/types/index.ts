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
