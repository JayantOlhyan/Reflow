import { 
  ContentItem, ContentListResponse, SocialAccount, PublishingJob, 
  SystemLog, Transcript, ContentBrief, GeneratedContent,
  CarouselItem, CarouselListResponse, CarouselSlideItem,
  ClipItem, ClipListResponse
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  public baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
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

  async getContentList(params?: { page?: number; limit?: number; type?: string; status?: string; search?: string }): Promise<ContentListResponse> {
    const query = new URLSearchParams();
    if (params?.page) query.set('page', params.page.toString());
    if (params?.limit) query.set('limit', params.limit.toString());
    if (params?.type && params.type !== 'all') query.set('type', params.type.toUpperCase());
    if (params?.status) query.set('status', params.status.toUpperCase());
    if (params?.search) query.set('search', params.search);

    const queryString = query.toString();
    const endpoint = `/api/content${queryString ? `?${queryString}` : ''}`;
    return this.request<ContentListResponse>(endpoint);
  }

  async getContent(id: string): Promise<ContentItem> {
    return this.request<ContentItem>(`/api/content/${id}`);
  }

  async uploadFile(file: File, title?: string): Promise<ContentItem> {
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);

    return this.request<ContentItem>('/api/content/upload', {
      method: 'POST',
      body: formData
    });
  }

  async createTextContent(title: string, text: string): Promise<ContentItem> {
    return this.request<ContentItem>('/api/content/text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, text })
    });
  }

  async reprocessMedia(contentId: string): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/api/content/${contentId}/reprocess`, {
      method: 'POST'
    });
  }

  async deleteContent(id: string): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/api/content/${id}`, {
      method: 'DELETE'
    });
  }

  getAssetUrl(contentId: string, assetId: string): string {
    return `${this.baseUrl}/api/content/${contentId}/asset/${assetId}`;
  }

  getVariantUrl(contentId: string, variantId: string): string {
    return `${this.baseUrl}/api/content/${contentId}/variant/${variantId}`;
  }

  // Phase 3 AI Intelligence Methods
  async getTranscript(contentId: string): Promise<Transcript> {
    return this.request<Transcript>(`/api/content/${contentId}/transcript`);
  }

  async getContentBrief(contentId: string): Promise<ContentBrief> {
    return this.request<ContentBrief>(`/api/content/${contentId}/brief`);
  }

  async getGeneratedContent(contentId: string): Promise<GeneratedContent[]> {
    return this.request<GeneratedContent[]>(`/api/content/${contentId}/generated`);
  }

  async triggerAiGeneration(contentId: string, platforms: string[] = ["LINKEDIN", "INSTAGRAM", "X", "YOUTUBE"], tone: string = "professional") {
    return this.request<{ status: string; message: string }>(`/api/content/${contentId}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platforms, tone })
    });
  }

  async regeneratePlatform(contentId: string, platform: string, tone: string = "professional") {
    return this.request<{ status: string; message: string }>(`/api/content/${contentId}/regenerate/${platform}?tone=${tone}`, {
      method: 'POST'
    });
  }

  // Phase 4 Carousel Engine API
  async getCarousels(page: number = 1, limit: number = 20): Promise<CarouselListResponse> {
    return this.request<CarouselListResponse>(`/api/carousels?page=${page}&limit=${limit}`);
  }

  async getCarousel(carouselId: string): Promise<CarouselItem> {
    return this.request<CarouselItem>(`/api/carousels/${carouselId}`);
  }

  async createCarousel(title: string, template: string = "MINIMAL", contentId?: string): Promise<CarouselItem> {
    return this.request<CarouselItem>('/api/carousels', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, template, content_id: contentId })
    });
  }

  async updateCarousel(carouselId: string, data: { title?: string; template?: string; aspect_ratio?: string }): Promise<CarouselItem> {
    return this.request<CarouselItem>(`/api/carousels/${carouselId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
  }

  async deleteCarousel(carouselId: string): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/api/carousels/${carouselId}`, {
      method: 'DELETE'
    });
  }

  async generateCarouselAI(carouselId: string, slideCount: number = 5, template: string = "MINIMAL", customPrompt?: string) {
    return this.request<{ status: string; message: string }>(`/api/carousels/${carouselId}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slide_count: slideCount, template, custom_prompt: customPrompt })
    });
  }

  async addSlide(carouselId: string, headline: string, body: string, tag?: string): Promise<CarouselItem> {
    return this.request<CarouselItem>(`/api/carousels/${carouselId}/slides`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ headline, body, tag })
    });
  }

  async updateSlide(carouselId: string, slideId: string, data: { headline?: string; body?: string; tag?: string; layout?: string; background?: string }): Promise<CarouselItem> {
    return this.request<CarouselItem>(`/api/carousels/${carouselId}/slides/${slideId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
  }

  async deleteSlide(carouselId: string, slideId: string): Promise<CarouselItem> {
    return this.request<CarouselItem>(`/api/carousels/${carouselId}/slides/${slideId}`, {
      method: 'DELETE'
    });
  }

  async reorderSlides(carouselId: string, slideIds: string[]): Promise<CarouselItem> {
    return this.request<CarouselItem>(`/api/carousels/${carouselId}/slides/reorder`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slide_ids: slideIds })
    });
  }

  async renderCarousel(carouselId: string): Promise<{ status: string; message: string; data: any }> {
    return this.request<{ status: string; message: string; data: any }>(`/api/carousels/${carouselId}/render`, {
      method: 'POST'
    });
  }

  getExportDownloadUrl(carouselId: string, exportId: string): string {
    return `${this.baseUrl}/api/carousels/${carouselId}/export/${exportId}`;
  }

  // Phase 5 Clip Engine
  async discoverClips(contentId: string, options?: { min_duration?: number; max_duration?: number; target_count?: number; force_refresh?: boolean }): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/api/content/${contentId}/clips/discover`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(options || {})
    });
  }

  async getContentClips(contentId: string): Promise<ClipListResponse> {
    return this.request<ClipListResponse>(`/api/content/${contentId}/clips`);
  }

  async getClip(clipId: string): Promise<ClipItem> {
    return this.request<ClipItem>(`/api/clips/${clipId}`);
  }

  async updateClip(clipId: string, data: { title?: string; hook?: string; start_time?: number; end_time?: number }): Promise<ClipItem> {
    return this.request<ClipItem>(`/api/clips/${clipId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
  }

  async generateClip(clipId: string, aspectRatios: string[] = ['9:16']): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/api/clips/${clipId}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ aspect_ratios: aspectRatios, include_thumbnail: true })
    });
  }

  async deleteClip(clipId: string): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/api/clips/${clipId}`, {
      method: 'DELETE'
    });
  }

  getClipVariantUrl(clipId: string, variantId: string): string {
    return `${this.baseUrl}/api/clips/${clipId}/variant/${variantId}`;
  }

  getClipStreamUrl(clipId: string): string {
    return `${this.baseUrl}/api/clips/${clipId}/stream`;
  }

  // Legacy Adapters
  async generateRepurpose(contentId: string, targetFormat: string, destinations: string[]) {
    return this.request<{
      content_id: string;
      target_format: string;
      outputs: Record<string, any>;
    }>('/api/repurpose/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content_id: contentId, target_format: targetFormat, destinations })
    });
  }

  async generateCarousel(topic: string, slideCount: number = 4) {
    return this.request<{ slides: any[] }>('/api/carousels/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform })
    });
  }

  async schedule(data: any) {
    return this.request<{ status: string; message: string; platform: string }>('/api/schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
  }
}

export const api = new ApiClient(API_BASE);

export async function fetchOverviewData() {
  try {
    return await api.getOverview();
  } catch {
    return null;
  }
}

export async function fetchContentList(): Promise<ContentItem[]> {
  try {
    const res = await api.getContentList();
    return res.items || [];
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
