import { ContentItem, SocialAccount, Workflow, ScheduledPost, PublishingJob, SystemLog, CarouselDeck } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(options?.headers || {})
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `API request failed with status ${response.status}`);
      }

      return await response.json();
    } catch (error: any) {
      console.error(`API Error [${endpoint}]:`, error.message);
      throw error;
    }
  }

  async getOverview() {
    return this.request<{
      metrics: { total: number; published: number; scheduled: number; failed: number };
      recent_activity: any[];
      connections: any[];
    }>('/api/overview');
  }

  async getContentList(): Promise<ContentItem[]> {
    return this.request<ContentItem[]>('/api/content');
  }

  async createContent(data: Partial<ContentItem>): Promise<ContentItem> {
    return this.request<ContentItem>('/api/content', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async deleteContent(id: string): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/api/content/${id}`, {
      method: 'DELETE'
    });
  }

  async generateRepurpose(contentId: string, targetFormat: string, destinations: string[]) {
    return this.request<{
      content_id: string;
      target_format: string;
      outputs: Record<string, { title: string; caption: string; hashtags: string; format: string }>;
    }>('/api/repurpose/generate', {
      method: 'POST',
      body: JSON.stringify({ content_id: contentId, target_format: targetFormat, destinations })
    });
  }

  async generateCarousel(topic: string, slideCount: number = 4) {
    return this.request<{ slides: any[] }>('/api/carousels/generate', {
      method: 'POST',
      body: JSON.stringify({ topic, slide_count: slideCount })
    });
  }

  async getConnections(): Promise<SocialAccount[]> {
    return this.request<SocialAccount[]>('/api/connections');
  }

  async getSystemHealth() {
    return this.request<{
      status: string;
      timestamp: string;
      components: Record<string, { status: string; details?: string }>;
    }>('/api/system/health');
  }

  async getSystemJobs() {
    return this.request<PublishingJob[]>('/api/system/jobs');
  }

  async getSystemLogs() {
    return this.request<SystemLog[]>('/api/system/logs');
  }

  async publish(platform: string) {
    return this.request<{ status: string; message: string; platform: string }>('/api/publish', {
      method: 'POST',
      body: JSON.stringify({ platform })
    });
  }

  async schedule(data: any) {
    return this.request<{ status: string; message: string; platform: string }>('/api/schedule', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }
}

export const api = new ApiClient(API_BASE);

// Legacy helpers for direct component consumption with proper fallback signatures
export async function fetchOverviewData() {
  try {
    return await api.getOverview();
  } catch {
    return null;
  }
}

export async function fetchContentList(): Promise<ContentItem[]> {
  try {
    return await api.getContentList();
  } catch {
    return [];
  }
}

export async function fetchConnections(): Promise<SocialAccount[]> {
  try {
    return await api.getConnections();
  } catch {
    return [];
  }
}
