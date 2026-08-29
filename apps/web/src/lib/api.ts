import { ContentItem, SocialAccount, Workflow, ScheduledPost, PublishingJob, SystemLog, CarouselDeck } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchOverviewData() {
  try {
    const res = await fetch(`${API_BASE}/api/overview`, { cache: 'no-store' });
    if (res.ok) return await res.json();
  } catch (e) {
    console.warn('Backend offline, using local store:', e);
  }
  return null;
}

export async function fetchContentList(): Promise<ContentItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/content`, { cache: 'no-store' });
    if (res.ok) return await res.json();
  } catch (e) {
    console.warn('Backend offline, using fallback:', e);
  }
  return [
    {
      id: 'cnt-1',
      title: 'Building an AI SaaS in 24 Hours',
      type: 'video',
      source: '/sample.mp4',
      thumbnail: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=600&auto=format&fit=crop&q=80',
      duration: 742,
      status: 'published',
      created_at: 'Aug 28, 2026',
      destinations: ['youtube', 'instagram', 'tiktok'],
      variants: [
        { platform: 'youtube', format: '16:9', status: 'published' },
        { platform: 'instagram', format: '9:16', status: 'published' },
        { platform: 'tiktok', format: '9:16', status: 'published' }
      ]
    },
    {
      id: 'cnt-2',
      title: '10 AI Tools that 10x Productivity',
      type: 'carousel',
      thumbnail: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=600&auto=format&fit=crop&q=80',
      slide_count: 8,
      status: 'published',
      created_at: 'Aug 27, 2026',
      destinations: ['linkedin', 'instagram'],
      variants: [
        { platform: 'linkedin', format: '4:5', status: 'published' },
        { platform: 'instagram', format: '1:1', status: 'published' }
      ]
    },
    {
      id: 'cnt-3',
      title: 'Automation Workflow Breakdown',
      type: 'image',
      thumbnail: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=600&auto=format&fit=crop&q=80',
      dimensions: '1080x1350',
      status: 'scheduled',
      created_at: 'Aug 26, 2026',
      destinations: ['x', 'linkedin'],
      variants: [
        { platform: 'x', format: '16:9', status: 'scheduled' },
        { platform: 'linkedin', format: '4:5', status: 'scheduled' }
      ]
    },
    {
      id: 'cnt-4',
      title: 'My Learnings From 30 Days of Building',
      type: 'text',
      thumbnail: 'https://images.unsplash.com/photo-1517842645767-c639042777db?w=600&auto=format&fit=crop&q=80',
      status: 'draft',
      created_at: 'Aug 25, 2026',
      destinations: ['x', 'linkedin'],
      variants: []
    }
  ];
}

export async function fetchConnections(): Promise<SocialAccount[]> {
  try {
    const res = await fetch(`${API_BASE}/api/connections`, { cache: 'no-store' });
    if (res.ok) return await res.json();
  } catch (e) {
    console.warn('Using fallback connections');
  }
  return [
    { id: 'youtube', name: 'YouTube', handle: '@JayantOlhyan', connected: true, capabilities: ['video', 'thumbnail', 'description', 'scheduling'] },
    { id: 'instagram', name: 'Instagram', handle: '@jayantolhyan', connected: true, capabilities: ['video', 'image', 'carousel', 'caption', 'scheduling'] },
    { id: 'tiktok', name: 'TikTok', handle: '@jayant.olhyan', connected: true, capabilities: ['video', 'caption', 'scheduling'] },
    { id: 'linkedin', name: 'LinkedIn', handle: 'Jayant Olhyan', connected: true, capabilities: ['video', 'image', 'carousel', 'text', 'scheduling'] },
    { id: 'x', name: 'X (Twitter)', handle: '@JayantOlhyan', connected: true, capabilities: ['video', 'image', 'text', 'thread', 'scheduling'] },
    { id: 'facebook', name: 'Facebook', handle: '', connected: false, capabilities: ['video', 'image', 'text', 'scheduling'] },
    { id: 'pinterest', name: 'Pinterest', handle: '', connected: false, capabilities: ['image', 'video', 'scheduling'] },
    { id: 'threads', name: 'Threads', handle: '', connected: false, capabilities: ['text', 'image', 'video', 'scheduling'] }
  ];
}
