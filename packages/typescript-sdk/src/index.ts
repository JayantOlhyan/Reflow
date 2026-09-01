export class ReflowError extends Error {
  constructor(message: string, public code: string = 'UNKNOWN_ERROR', public statusCode: number = 500) {
    super(message);
    this.name = 'ReflowError';
  }
}

export class AuthenticationError extends ReflowError {}
export class AuthorizationError extends ReflowError {}
export class ValidationError extends ReflowError {}
export class RateLimitError extends ReflowError {}
export class NotFoundError extends ReflowError {}
export class ConflictError extends ReflowError {}
export class ServerError extends ReflowError {}

export interface ReflowClientOptions {
  apiKey: string;
  baseUrl?: string;
  timeout?: number;
  maxRetries?: number;
}

export class ReflowClient {
  public apiKey: string;
  public baseUrl: string;
  public timeout: number;
  public maxRetries: number;

  public content: {
    list: (opts?: { page?: number; pageSize?: number; search?: string; type?: string }) => Promise<any>;
    listAll: (opts?: { search?: string; type?: string }) => AsyncGenerator<any, void, unknown>;
    get: (id: string) => Promise<any>;
    createText: (title: string, rawText: string) => Promise<any>;
    delete: (id: string) => Promise<any>;
  };

  public clips: {
    discover: (contentId: string) => Promise<{ job_id: string; status: string }>;
    list: (contentId: string) => Promise<any[]>;
    get: (id: string) => Promise<any>;
    generate: (id: string) => Promise<{ job_id: string; status: string }>;
  };

  public carousels: {
    create: (contentId: string, title: string, theme: string, slides: any[]) => Promise<any>;
    list: (contentId: string) => Promise<any[]>;
    get: (id: string) => Promise<any>;
    generate: (id: string) => Promise<{ job_id: string; status: string }>;
    export: (id: string, format?: string) => Promise<any>;
  };

  public governance: {
    evaluate: (contentId: string) => Promise<any>;
    get: (contentId: string) => Promise<any>;
  };

  public publications: {
    create: (data: { content_id: string; platform: string; post_type: string; caption: string; title?: string; scheduled_at?: string }, idempotencyKey?: string) => Promise<any>;
    publish: (id: string) => Promise<{ job_id: string; status: string }>;
  };

  public analytics: {
    overview: () => Promise<any>;
    getContent: (contentId: string) => Promise<any>;
  };

  public jobs: {
    get: (jobId: string) => Promise<any>;
    wait: (jobId: string, timeoutMs?: number, pollIntervalMs?: number) => Promise<any>;
  };

  constructor(options: ReflowClientOptions) {
    this.apiKey = options.apiKey;
    this.baseUrl = (options.baseUrl || 'http://localhost:8000/api/v1').replace(/\/$/, '');
    this.timeout = options.timeout || 30000;
    this.maxRetries = options.maxRetries || 3;

    const request = this.request.bind(this);

    this.content = {
      list: (opts) => request('GET', '/content', { params: opts }),
      listAll: async function* (opts) {
        let page = 1;
        while (true) {
          const res = await request('GET', '/content', { params: { ...opts, page, page_size: 50 } });
          const items = res.items || [];
          for (const item of items) {
            yield item;
          }
          if (page * 50 >= (res.total || 0) || items.length === 0) break;
          page++;
        }
      },
      get: (id) => request('GET', `/content/${id}`),
      createText: (title, rawText) => {
        const formData = new URLSearchParams();
        formData.append('title', title);
        formData.append('raw_text', rawText);
        return request('POST', '/content/text', { body: formData, headers: { 'Content-Type': 'application/x-www-form-urlencoded' } });
      },
      delete: (id) => request('DELETE', `/content/${id}`),
    };

    this.clips = {
      discover: (contentId) => request('POST', `/content/${contentId}/clips/discover`),
      list: (contentId) => request('GET', `/content/${contentId}/clips`),
      get: (id) => request('GET', `/clips/${id}`),
      generate: (id) => request('POST', `/clips/${id}/generate`),
    };

    this.carousels = {
      create: (contentId, title, theme, slides) => request('POST', `/content/${contentId}/carousels`, { body: JSON.stringify({ title, theme, slides }) }),
      list: (contentId) => request('GET', `/content/${contentId}/carousels`),
      get: (id) => request('GET', `/carousels/${id}`),
      generate: (id) => request('POST', `/carousels/${id}/generate`),
      export: (id, format = 'pdf') => request('POST', `/carousels/${id}/export?format=${format}`),
    };

    this.governance = {
      evaluate: (contentId) => request('POST', `/content/${contentId}/governance/evaluate`),
      get: (contentId) => request('GET', `/content/${contentId}/governance`),
    };

    this.publications = {
      create: (data, idempotencyKey) => {
        const headers: Record<string, string> = {};
        if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey;
        return request('POST', '/publications', { body: JSON.stringify(data), headers });
      },
      publish: (id) => request('POST', `/publications/${id}/publish`),
    };

    this.analytics = {
      overview: () => request('GET', '/analytics/overview'),
      getContent: (contentId) => request('GET', `/analytics/content/${contentId}`),
    };

    this.jobs = {
      get: (jobId) => request('GET', `/jobs/${jobId}`),
      wait: async (jobId, timeoutMs = 60000, pollIntervalMs = 2000) => {
        const start = Date.now();
        while (Date.now() - start < timeoutMs) {
          const res = await request('GET', `/jobs/${jobId}`);
          if (['SUCCEEDED', 'FAILED', 'STALE'].includes(res.status)) {
            return res;
          }
          await new Promise((r) => setTimeout(r, pollIntervalMs));
        }
        throw new Error(`Job '${jobId}' timed out after ${timeoutMs}ms.`);
      },
    };
  }

  private async request(method: string, path: string, options: { params?: Record<string, any>; body?: any; headers?: Record<string, string> } = {}): Promise<any> {
    let url = `${this.baseUrl}${path}`;
    if (options.params) {
      const qp = new URLSearchParams();
      Object.entries(options.params).forEach(([k, v]) => {
        if (v !== undefined && v !== null) qp.append(k, String(v));
      });
      if (qp.toString()) url += `?${qp.toString()}`;
    }

    const headers: Record<string, string> = {
      'Authorization': `Bearer ${this.apiKey}`,
      'Accept': 'application/json',
      ...(options.body && typeof options.body === 'string' && !options.headers?.['Content-Type'] ? { 'Content-Type': 'application/json' } : {}),
      ...(options.headers || {}),
    };

    let attempts = 0;
    while (attempts <= this.maxRetries) {
      attempts++;
      try {
        const res = await fetch(url, { method, headers, body: options.body });
        if ([429, 502, 503, 504].includes(res.status) && attempts <= this.maxRetries) {
          const retryAfter = parseFloat(res.headers.get('Retry-After') || '1');
          await new Promise((r) => setTimeout(r, retryAfter * 1000));
          continue;
        }

        if (!res.ok) {
          let errCode = 'HTTP_ERROR';
          let errMsg = res.statusText;
          try {
            const data = await res.json();
            if (data.error) {
              errCode = data.error.code || errCode;
              errMsg = data.error.message || errMsg;
            }
          } catch {}

          if (res.status === 401) throw new AuthenticationError(errMsg, errCode, res.status);
          if (res.status === 403) throw new AuthorizationError(errMsg, errCode, res.status);
          if (res.status === 404) throw new NotFoundError(errMsg, errCode, res.status);
          if (res.status === 409) throw new ConflictError(errMsg, errCode, res.status);
          if (res.status === 400 || res.status === 422) throw new ValidationError(errMsg, errCode, res.status);
          if (res.status === 429) throw new RateLimitError(errMsg, errCode, res.status);
          if (res.status >= 500) throw new ServerError(errMsg, errCode, res.status);
          throw new ReflowError(errMsg, errCode, res.status);
        }

        return await res.json();
      } catch (err: any) {
        if (err instanceof ReflowError) throw err;
        if (attempts > this.maxRetries) {
          throw new ServerError(`Network request failed: ${err.message}`, 'NETWORK_ERROR', 503);
        }
        await new Promise((r) => setTimeout(r, 1000));
      }
    }
  }
}
