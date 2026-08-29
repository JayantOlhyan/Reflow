export type ContentType = 'video' | 'carousel' | 'image' | 'text';
export type ContentStatus = 'draft' | 'processing' | 'scheduled' | 'published' | 'failed';

export interface ContentVariant {
  platform: 'youtube' | 'instagram' | 'tiktok' | 'linkedin' | 'x' | 'facebook' | 'pinterest' | 'threads';
  format: '16:9' | '9:16' | '1:1' | '4:5' | 'Text' | 'PDF' | 'Reel' | 'Short' | 'Thread' | 'Post';
  status: ContentStatus;
  storage_path?: string;
  copy?: string;
}

export interface ContentItem {
  id: string;
  title: string;
  type: ContentType;
  source?: string;
  thumbnail?: string;
  duration?: number;
  slide_count?: number;
  dimensions?: string;
  status: ContentStatus;
  created_at: string;
  destinations: string[];
  variants?: ContentVariant[];
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
  status: ContentStatus;
}

export interface PublishingJob {
  id: string;
  content_title: string;
  platform: string;
  status: ContentStatus;
  time: string;
  retry_count: number;
  error?: string;
}

export interface SystemLog {
  id: string;
  level: 'INFO' | 'WARN' | 'ERROR';
  timestamp: string;
  service: string;
  message: string;
}
