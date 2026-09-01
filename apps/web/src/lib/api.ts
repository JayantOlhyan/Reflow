import { 
  ContentItem, ContentListResponse, SocialAccount, PublishingJob, 
  SystemLog, Transcript, ContentBrief, GeneratedContent,
  CarouselItem, CarouselListResponse, CarouselSlideItem,
  ClipItem, ClipListResponse, CaptionCue, ClipCaptionsData,
  PlatformConnectionItem, PublicationItem, PublicationCreateData,
  BatchPublicationCreateData, BatchPublicationResponse,
  SchedulePublicationCreateData, SchedulePublicationResponse,
  RescheduleData, CalendarEventItem, CalendarResponse,
  PostMetricSnapshot, PublicationAnalytics, AnalyticsOverview,
  AnalyticsTimeseriesItem, AnalyticsTimeseriesResponse,
  PlatformAnalyticsItem, ContentAnalyticsItem
} from '@/types';

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
  async getCarousels(contentIdOrPage?: string | number, limit: number = 20): Promise<CarouselListResponse> {
    if (typeof contentIdOrPage === 'string') {
      return this.request<CarouselListResponse>(`/api/carousels?content_id=${encodeURIComponent(contentIdOrPage)}`);
    }
    const page = typeof contentIdOrPage === 'number' ? contentIdOrPage : 1;
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

  async getClips(contentId?: string): Promise<ClipListResponse> {
    if (contentId) return this.getContentClips(contentId);
    return this.request<ClipListResponse>('/api/clips');
  }

  async getGovernanceResult(contentId: string): Promise<any> {
    return this.request<any>(`/api/content/${contentId}/governance`);
  }

  async uploadContent(file: File, title?: string): Promise<ContentItem> {
    return this.uploadFile(file, title);
  }

  async getClip(clipId: string): Promise<ClipItem> {
    return this.request<ClipItem>(`/api/clips/${clipId}`);
  }

  async updateClip(clipId: string, data: {
    title?: string;
    hook?: string;
    start_time?: number;
    end_time?: number;
    caption_style?: string;
    caption_enabled?: boolean;
    highlight_keywords?: string[];
  }): Promise<ClipItem> {
    return this.request<ClipItem>(`/api/clips/${clipId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
  }

  async generateClip(
    clipId: string,
    options?: {
      aspect_ratios?: string[];
      include_thumbnail?: boolean;
      burn_captions?: boolean;
      caption_style?: string;
      highlight_keywords?: string[];
    } | string[],
    burnCaptions: boolean = false,
    captionStyle?: string
  ): Promise<{ status: string; message: string }> {
    let payload: any = {};
    if (Array.isArray(options)) {
      payload = {
        aspect_ratios: options,
        include_thumbnail: true,
        burn_captions: burnCaptions,
        caption_style: captionStyle
      };
    } else if (typeof options === 'object' && options !== null) {
      payload = {
        aspect_ratios: options.aspect_ratios || ['9:16'],
        include_thumbnail: options.include_thumbnail !== false,
        burn_captions: !!options.burn_captions,
        caption_style: options.caption_style,
        highlight_keywords: options.highlight_keywords
      };
    } else {
      payload = {
        aspect_ratios: ['9:16'],
        include_thumbnail: true,
        burn_captions: burnCaptions,
        caption_style: captionStyle
      };
    }

    return this.request<{ status: string; message: string }>(`/api/clips/${clipId}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  }

  async getClipCaptions(clipId: string): Promise<ClipCaptionsData> {
    return this.request<ClipCaptionsData>(`/api/clips/${clipId}/captions`);
  }

  async updateClipCaptions(clipId: string, data: {
    caption_style?: string;
    caption_enabled?: boolean;
    highlight_keywords?: string[];
    custom_settings?: any;
  }): Promise<ClipCaptionsData> {
    return this.request<ClipCaptionsData>(`/api/clips/${clipId}/captions`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
  }

  async renderClipCaptions(
    clipId: string,
    aspectRatios: string[] = ['9:16'],
    captionStyle?: string,
    highlightKeywords?: string[]
  ): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/api/clips/${clipId}/render-captions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        aspect_ratios: aspectRatios,
        caption_style: captionStyle,
        highlight_keywords: highlightKeywords
      })
    });
  }

  getClipSrtUrl(clipId: string): string {
    return `${this.baseUrl}/api/clips/${clipId}/captions/export.srt`;
  }

  getClipVttUrl(clipId: string): string {
    return `${this.baseUrl}/api/clips/${clipId}/captions/export.vtt`;
  }

  async deleteClip(clipId: string): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/api/clips/${clipId}`, {
      method: 'DELETE'
    });
  }

  getClipVariantUrl(clipId: string, variantId: string): string {
    return `${this.baseUrl}/api/clips/${clipId}/variant/${variantId}`;
  }

  getClipStreamUrl(clipId: string, preferCaptions: boolean = false): string {
    return `${this.baseUrl}/api/clips/${clipId}/stream${preferCaptions ? '?prefer_captions=true' : ''}`;
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

  // Phase 7 Platform Connections & Publications
  async getPlatformConnections(): Promise<{ items: PlatformConnectionItem[]; total: number }> {
    return this.request<{ items: PlatformConnectionItem[]; total: number }>('/api/connections');
  }

  async getPlatformConnection(id: string): Promise<PlatformConnectionItem> {
    return this.request<PlatformConnectionItem>(`/api/connections/${id}`);
  }

  async startPlatformOAuth(platform: string): Promise<{ platform: string; authorization_url: string; state: string }> {
    return this.request<{ platform: string; authorization_url: string; state: string }>(`/api/connections/${platform}/start`, {
      method: 'POST'
    });
  }

  async startYouTubeOAuth(): Promise<{ platform: string; authorization_url: string; state: string }> {
    return this.startPlatformOAuth('youtube');
  }

  async disconnectConnection(connectionId: string): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/api/connections/${connectionId}/disconnect`, {
      method: 'POST'
    });
  }

  async refreshConnection(connectionId: string): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/api/connections/${connectionId}/refresh`, {
      method: 'POST'
    });
  }

  async createPublication(data: PublicationCreateData): Promise<PublicationItem> {
    return this.request<PublicationItem>('/api/publications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
  }

  async createBatchPublications(data: BatchPublicationCreateData): Promise<BatchPublicationResponse> {
    return this.request<BatchPublicationResponse>('/api/publications/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
  }

  async getPublications(contentId?: string): Promise<{ items: PublicationItem[]; total: number }> {
    const qs = contentId ? `?content_id=${encodeURIComponent(contentId)}` : '';
    return this.request<{ items: PublicationItem[]; total: number }>(`/api/publications${qs}`);
  }

  async getPublication(pubId: string): Promise<PublicationItem> {
    return this.request<PublicationItem>(`/api/publications/${pubId}`);
  }

  async retryPublication(pubId: string): Promise<PublicationItem> {
    return this.request<PublicationItem>(`/api/publications/${pubId}/retry`, {
      method: 'POST'
    });
  }

  async cancelPublication(pubId: string): Promise<PublicationItem> {
    return this.request<PublicationItem>(`/api/publications/${pubId}/cancel`, {
      method: 'POST'
    });
  }

  async schedulePublications(data: SchedulePublicationCreateData): Promise<SchedulePublicationResponse> {
    return this.request<SchedulePublicationResponse>('/api/publications/schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
  }

  async getScheduledPublications(): Promise<{ items: PublicationItem[]; total: number }> {
    return this.request<{ items: PublicationItem[]; total: number }>('/api/publications/scheduled');
  }

  async getCalendarEvents(params: {
    start: string;
    end: string;
    timezone?: string;
    platform?: string;
    status?: string;
  }): Promise<CalendarResponse> {
    const query = new URLSearchParams();
    query.set('start', params.start);
    query.set('end', params.end);
    if (params.timezone) query.set('timezone', params.timezone);
    if (params.platform) query.set('platform', params.platform);
    if (params.status) query.set('status', params.status);
    return this.request<CalendarResponse>(`/api/calendar?${query.toString()}`);
  }

  async reschedulePublication(pubId: string, data: RescheduleData): Promise<PublicationItem> {
    return this.request<PublicationItem>(`/api/publications/${pubId}/reschedule`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
  }

  // Phase 10: Analytics & Performance Intelligence API Methods
  async getAnalyticsOverview(params?: { start?: string; end?: string; platform?: string; content_type?: string }): Promise<AnalyticsOverview> {
    const query = new URLSearchParams();
    if (params?.start) query.set('start', params.start);
    if (params?.end) query.set('end', params.end);
    if (params?.platform) query.set('platform', params.platform);
    if (params?.content_type) query.set('content_type', params.content_type);
    return this.request<AnalyticsOverview>(`/api/analytics/overview?${query.toString()}`);
  }

  async getAnalyticsTimeseries(params?: { start?: string; end?: string; platform?: string }): Promise<AnalyticsTimeseriesResponse> {
    const query = new URLSearchParams();
    if (params?.start) query.set('start', params.start);
    if (params?.end) query.set('end', params.end);
    if (params?.platform) query.set('platform', params.platform);
    return this.request<AnalyticsTimeseriesResponse>(`/api/analytics/timeseries?${query.toString()}`);
  }

  async getPlatformAnalytics(params?: { start?: string; end?: string }): Promise<PlatformAnalyticsItem[]> {
    const query = new URLSearchParams();
    if (params?.start) query.set('start', params.start);
    if (params?.end) query.set('end', params.end);
    return this.request<PlatformAnalyticsItem[]>(`/api/analytics/platforms?${query.toString()}`);
  }

  async getContentAnalytics(params?: { start?: string; end?: string; content_type?: string; sort_by?: string }): Promise<ContentAnalyticsItem[]> {
    const query = new URLSearchParams();
    if (params?.start) query.set('start', params.start);
    if (params?.end) query.set('end', params.end);
    if (params?.content_type) query.set('content_type', params.content_type);
    if (params?.sort_by) query.set('sort_by', params.sort_by);
    return this.request<ContentAnalyticsItem[]>(`/api/analytics/content?${query.toString()}`);
  }

  async getPublicationAnalytics(pubId: string): Promise<PublicationAnalytics> {
    return this.request<PublicationAnalytics>(`/api/analytics/publications/${pubId}`);
  }

  async refreshPublicationAnalytics(pubId: string): Promise<{ status: string; job_id: string; message: string }> {
    return this.request<{ status: string; job_id: string; message: string }>(`/api/analytics/publications/${pubId}/refresh`, {
      method: 'POST'
    });
  }

  async backfillAnalytics(data?: { start_date?: string; end_date?: string; platform?: string; limit?: number }): Promise<{ queued_count: number; message: string }> {
    return this.request<{ queued_count: number; message: string }>('/api/analytics/backfill', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data || {})
    });
  }

  getAnalyticsExportUrl(params?: { start?: string; end?: string; platform?: string }): string {
    const query = new URLSearchParams();
    if (params?.start) query.set('start', params.start);
    if (params?.end) query.set('end', params.end);
    if (params?.platform) query.set('platform', params.platform);
    return `${this.baseUrl}/api/analytics/export?${query.toString()}`;
  }

  // Phase 11: Content Intelligence & Recommendations
  async getIntelligenceOverview(): Promise<import('@/types').IntelligenceOverview> {
    return this.request<import('@/types').IntelligenceOverview>('/api/intelligence/overview');
  }

  async getIntelligenceInsights(scope?: string): Promise<import('@/types').PerformanceInsight[]> {
    const query = scope ? `?scope=${encodeURIComponent(scope)}` : '';
    return this.request<import('@/types').PerformanceInsight[]>(`/api/intelligence/insights${query}`);
  }

  async getContentRecommendations(status: string = 'ACTIVE', type?: string): Promise<import('@/types').ContentRecommendation[]> {
    const params = new URLSearchParams({ status });
    if (type) params.set('type', type);
    return this.request<import('@/types').ContentRecommendation[]>(`/api/intelligence/recommendations?${params.toString()}`);
  }

  async getContentPatterns(pattern_type?: string): Promise<import('@/types').ContentPattern[]> {
    const query = pattern_type ? `?pattern_type=${encodeURIComponent(pattern_type)}` : '';
    return this.request<import('@/types').ContentPattern[]>(`/api/intelligence/patterns${query}`);
  }

  async getTopicPerformance(): Promise<import('@/types').TopicPerformanceItem[]> {
    return this.request<import('@/types').TopicPerformanceItem[]>('/api/intelligence/topics');
  }

  async getHookPerformance(): Promise<import('@/types').HookPerformanceItem[]> {
    return this.request<import('@/types').HookPerformanceItem[]>('/api/intelligence/hooks');
  }

  async getDurationPerformance(): Promise<import('@/types').DurationPerformanceItem[]> {
    return this.request<import('@/types').DurationPerformanceItem[]>('/api/intelligence/durations');
  }

  async getPostingWindows(): Promise<import('@/types').PostingWindowItem[]> {
    return this.request<import('@/types').PostingWindowItem[]>('/api/intelligence/posting-windows');
  }

  async getContentGaps(): Promise<import('@/types').ContentGapItem[]> {
    return this.request<import('@/types').ContentGapItem[]>('/api/intelligence/content-gaps');
  }

  async getExperiments(userId?: string): Promise<import('@/types').Experiment[]> {
    return this.getExperimentsList(userId);
  }

  async getExperimentsList(userId?: string): Promise<import('@/types').Experiment[]> {
    return this.request<import('@/types').Experiment[]>('/api/experiments', {
      headers: userId ? { 'X-User-Id': userId } : undefined
    });
  }

  async getExperimentDetails(id: string, userId?: string): Promise<import('@/types').ExperimentDetailResponse> {
    return this.request<import('@/types').ExperimentDetailResponse>(`/api/experiments/${id}`, {
      headers: userId ? { 'X-User-Id': userId } : undefined
    });
  }

  async createExperiment(data: any, userId?: string): Promise<import('@/types').ExperimentDetailResponse> {
    return this.request<import('@/types').ExperimentDetailResponse>('/api/experiments', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(userId ? { 'X-User-Id': userId } : {})
      },
      body: JSON.stringify(data)
    });
  }

  async startExperiment(id: string, userId?: string): Promise<import('@/types').ExperimentDetailResponse> {
    return this.request<import('@/types').ExperimentDetailResponse>(`/api/experiments/${id}/start`, {
      method: 'POST',
      headers: userId ? { 'X-User-Id': userId } : undefined
    });
  }

  async refreshExperiment(id: string, userId?: string) {
    return this.request<{ status: string; message: string; data: { job_id: string } }>(`/api/experiments/${id}/refresh`, {
      method: 'POST',
      headers: userId ? { 'X-User-Id': userId } : undefined
    });
  }

  exportExperimentsCsvUrl(userId?: string): string {
    return `${this.baseUrl}/api/experiments/export${userId ? `?user_id=${userId}` : ''}`;
  }

  async refreshIntelligence(): Promise<import('@/types').IntelligenceRefreshResponse> {
    return this.request<import('@/types').IntelligenceRefreshResponse>('/api/intelligence/refresh', {
      method: 'POST'
    });
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

  // Phase 13 Automation Endpoints
  async getAutomationRules(userId?: string): Promise<import('@/types').AutomationRule[]> {
    return this.request<import('@/types').AutomationRule[]>('/api/automations', {
      headers: userId ? { 'X-User-Id': userId } : undefined
    });
  }

  async getAutomationRule(id: string, userId?: string): Promise<import('@/types').AutomationDetailResponse> {
    return this.request<import('@/types').AutomationDetailResponse>(`/api/automations/${id}`, {
      headers: userId ? { 'X-User-Id': userId } : undefined
    });
  }

  async createAutomationRule(data: any, userId?: string): Promise<import('@/types').AutomationRule> {
    return this.request<import('@/types').AutomationRule>('/api/automations', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(userId ? { 'X-User-Id': userId } : {})
      },
      body: JSON.stringify(data)
    });
  }

  async updateAutomationRule(id: string, data: any, userId?: string): Promise<import('@/types').AutomationRule> {
    return this.request<import('@/types').AutomationRule>(`/api/automations/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...(userId ? { 'X-User-Id': userId } : {})
      },
      body: JSON.stringify(data)
    });
  }

  async deleteAutomationRule(id: string, userId?: string): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/api/automations/${id}`, {
      method: 'DELETE',
      headers: userId ? { 'X-User-Id': userId } : undefined
    });
  }

  async enableAutomationRule(id: string, userId?: string): Promise<import('@/types').AutomationRule> {
    return this.request<import('@/types').AutomationRule>(`/api/automations/${id}/enable`, {
      method: 'POST',
      headers: userId ? { 'X-User-Id': userId } : undefined
    });
  }

  async disableAutomationRule(id: string, userId?: string): Promise<import('@/types').AutomationRule> {
    return this.request<import('@/types').AutomationRule>(`/api/automations/${id}/disable`, {
      method: 'POST',
      headers: userId ? { 'X-User-Id': userId } : undefined
    });
  }

  async runAutomationRuleManual(id: string, entityId: string, userId?: string): Promise<import('@/types').AutomationExecution> {
    return this.request<import('@/types').AutomationExecution>(`/api/automations/${id}/run?entity_id=${encodeURIComponent(entityId)}`, {
      method: 'POST',
      headers: userId ? { 'X-User-Id': userId } : undefined
    });
  }

  async dryRunAutomationRule(id: string, entityId: string, userId?: string): Promise<{
    status: string;
    conditions_passed: boolean;
    skip_reason?: string | null;
    actions_to_execute: string[];
    preview_message: string;
  }> {
    return this.request<{
      status: string;
      conditions_passed: boolean;
      skip_reason?: string | null;
      actions_to_execute: string[];
      preview_message: string;
    }>(`/api/automations/${id}/dry-run?entity_id=${encodeURIComponent(entityId)}`, {
      method: 'POST',
      headers: userId ? { 'X-User-Id': userId } : undefined
    });
  }

  async createAutomationRuleFromTemplate(template: string, name: string, userId?: string): Promise<import('@/types').AutomationRule> {
    return this.request<import('@/types').AutomationRule>(`/api/automation-templates/${template}/create?name=${encodeURIComponent(name)}`, {
      method: 'POST',
      headers: userId ? { 'X-User-Id': userId } : undefined
    });
  }

  async getReadinessStatus(): Promise<{
    status: string;
    version: string;
    dependencies: Record<string, { status: string; details?: string }>;
  }> {
    return this.request('/health/ready');
  }

  async getSystemMetrics(): Promise<{
    status: string;
    version: string;
    cpu: { usage_percent: number; count: number } | null;
    memory: { total_mb: number; used_mb: number; free_mb: number; usage_percent: number } | null;
    disk: { total_gb: number; used_gb: number; free_gb: number; usage_percent: number; warning: boolean } | null;
    database_connected: boolean | null;
    redis_connected: boolean | null;
  }> {
    return this.request('/api/system/metrics');
  }

  async getSystemSettings(): Promise<{
    status: string;
    settings: {
      gemini_configured: boolean;
      openai_configured: boolean;
      anthropic_configured: boolean;
      storage_provider: string;
      storage_dir: string;
      max_upload_size_mb: number;
      deployment_mode: string;
      version: string;
    };
  }> {
    return this.request('/api/system/settings');
  }

  async updateSystemSettings(data: {
    gemini_api_key?: string;
    openai_api_key?: string;
    anthropic_api_key?: string;
    storage_provider?: string;
  }): Promise<{ status: string; message: string }> {
    return this.request('/api/system/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
  }

  // Phase 16: Notifications & Search APIs
  async getNotifications(limit = 50, unreadOnly = false): Promise<{ items: any[]; unread_count: number }> {
    const qs = `?limit=${limit}&unread_only=${unreadOnly}`;
    return this.request<{ items: any[]; unread_count: number }>(`/api/notifications${qs}`);
  }

  async markNotificationRead(id: string): Promise<{ status: string }> {
    return this.request<{ status: string }>(`/api/notifications/${id}/read`, {
      method: 'POST'
    });
  }

  async markAllNotificationsRead(): Promise<{ status: string; marked_read_count: number }> {
    return this.request<{ status: string; marked_read_count: number }>('/api/notifications/read-all', {
      method: 'POST'
    });
  }

  async searchEntities(q: string): Promise<{ query: string; results: any[] }> {
    return this.request<{ query: string; results: any[] }>(`/api/search?q=${encodeURIComponent(q)}`);
  }

  async approvePublication(pubId: string): Promise<PublicationItem> {
    return this.request<PublicationItem>(`/api/publications/${pubId}/approve`, {
      method: 'POST'
    });
  }

  async approveBatchPublications(publicationIds: string[]): Promise<{ status: string; approved_count: number; skipped_count: number }> {
    return this.request<{ status: string; approved_count: number; skipped_count: number }>('/api/publications/approve-batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(publicationIds)
    });
  }

  async getClipDetail(clipId: string): Promise<ClipItem> {
    return this.request<ClipItem>(`/api/clips/${clipId}`);
  }

  async getCarouselDetail(carouselId: string): Promise<CarouselItem> {
    return this.request<CarouselItem>(`/api/carousels/${carouselId}`);
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
