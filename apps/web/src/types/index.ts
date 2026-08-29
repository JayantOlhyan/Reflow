export type ContentType = 'VIDEO' | 'IMAGE' | 'PDF' | 'TEXT' | 'CAROUSEL' | 'video' | 'image' | 'pdf' | 'text' | 'carousel';
export type ContentStatus = 'UPLOADING' | 'READY' | 'FAILED' | 'DRAFT' | 'draft' | 'processing' | 'scheduled' | 'published' | 'failed';

export interface ContentVariant {
  platform: string;
  format: string;
  status: string;
  storage_path?: string;
  copy?: string;
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
