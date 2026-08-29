"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { 
  Plus, 
  Search, 
  Filter, 
  ArrowUpDown, 
  Video, 
  Layers, 
  Image as ImageIcon, 
  FileText, 
  Sparkles, 
  Upload, 
  X 
} from 'lucide-react';
import { ContentItem, ContentType } from '@/types';
import { YoutubeIcon, InstagramIcon, TiktokIcon, LinkedinIcon, XIcon } from '@/components/ui/SocialIcons';

export default function ContentLibraryPage() {
  const [activeTab, setActiveTab] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  const [items, setItems] = useState<ContentItem[]>([
    {
      id: 'cnt-1',
      title: 'Building an AI SaaS in 24 hours',
      type: 'video',
      thumbnail: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=600&auto=format&fit=crop&q=80',
      duration: 762,
      dimensions: '4K - 16:9',
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
  ]);

  const tabs = [
    { id: 'all', label: 'All' },
    { id: 'video', label: 'Videos' },
    { id: 'carousel', label: 'Carousels' },
    { id: 'image', label: 'Images' },
    { id: 'text', label: 'Text' },
    { id: 'draft', label: 'Drafts' },
  ];

  const filteredItems = items.filter(item => {
    if (activeTab === 'draft') return item.status === 'draft';
    if (activeTab !== 'all' && item.type !== activeTab) return false;
    if (searchQuery && !item.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const formatDurationBadge = (seconds?: number) => {
    if (!seconds) return null;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getPlatformIcon = (p: string) => {
    switch (p) {
      case 'youtube': return <YoutubeIcon className="w-3.5 h-3.5 text-red-400" />;
      case 'instagram': return <InstagramIcon className="w-3.5 h-3.5 text-pink-400" />;
      case 'linkedin': return <LinkedinIcon className="w-3.5 h-3.5 text-blue-400" />;
      case 'x': return <XIcon className="w-3 h-3 text-gray-300" />;
      case 'tiktok': return <TiktokIcon className="w-3.5 h-3.5 text-cyan-400" />;
      default: return null;
    }
  };

  const handleUploadSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const title = formData.get('title') as string;
    const type = formData.get('type') as ContentType;

    const newItem: ContentItem = {
      id: `cnt-${Date.now()}`,
      title: title || 'New Content Asset',
      type: type || 'video',
      thumbnail: 'https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=600&auto=format&fit=crop&q=80',
      duration: type === 'video' ? 180 : undefined,
      slide_count: type === 'carousel' ? 5 : undefined,
      status: 'draft',
      created_at: 'Just now',
      destinations: ['instagram', 'youtube']
    };

    setItems([newItem, ...items]);
    setIsUploadModalOpen(false);
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header & Main Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Content Library</h1>
          <p className="text-xs text-gray-400 mt-0.5">Manage, transform, and repurpose your source assets.</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-lg shadow-indigo-500/20 transition-all"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload Content</span>
          </button>
        </div>
      </div>

      {/* Tabs and Controls Filter Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pt-2">
        <div className="flex items-center gap-1 bg-[#111827] p-1 rounded-xl border border-[#1F2937] overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-[#161B26]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search content..."
              className="bg-[#111827] border border-[#1F2937] focus:border-indigo-500 rounded-xl pl-8 pr-3 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none w-48 transition-all"
            />
          </div>

          <button className="p-2 text-gray-400 hover:text-white rounded-xl bg-[#111827] border border-[#1F2937] hover:bg-[#161B26] transition-colors">
            <Filter className="w-3.5 h-3.5" />
          </button>
          <button className="p-2 text-gray-400 hover:text-white rounded-xl bg-[#111827] border border-[#1F2937] hover:bg-[#161B26] transition-colors">
            <ArrowUpDown className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Grid of Content Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {filteredItems.map((item) => (
          <div
            key={item.id}
            className="group bg-[#111827]/90 border border-[#1F2937] hover:border-indigo-500/50 rounded-2xl overflow-hidden transition-all duration-200 flex flex-col hover:shadow-xl hover:shadow-indigo-500/5"
          >
            <div className="relative aspect-[16/10] bg-[#161B26] overflow-hidden">
              <img
                src={item.thumbnail}
                alt={item.title}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[#0B0D12]/90 via-transparent to-transparent" />

              <div className="absolute top-2.5 left-2.5 flex items-center gap-1.5 bg-[#0B0D12]/80 backdrop-blur-md px-2 py-1 rounded-lg border border-white/10 text-[10px] font-semibold text-gray-200">
                {item.type === 'video' && <Video className="w-3 h-3 text-red-400" />}
                {item.type === 'carousel' && <Layers className="w-3 h-3 text-purple-400" />}
                {item.type === 'image' && <ImageIcon className="w-3 h-3 text-emerald-400" />}
                {item.type === 'text' && <FileText className="w-3 h-3 text-cyan-400" />}
                <span className="capitalize">{item.type}</span>
              </div>

              <div className="absolute bottom-2.5 right-2.5 bg-[#0B0D12]/90 backdrop-blur-md px-2 py-0.5 rounded text-[10px] font-medium text-gray-300">
                {item.duration ? formatDurationBadge(item.duration) : item.slide_count ? `${item.slide_count} Slides` : item.dimensions || 'Draft'}
              </div>
            </div>

            <div className="p-4 flex-1 flex flex-col justify-between space-y-3">
              <div>
                <h3 className="text-xs font-semibold text-white line-clamp-1 group-hover:text-indigo-300 transition-colors">
                  {item.title}
                </h3>
                <p className="text-[11px] text-gray-400 mt-1">
                  {item.created_at} • {item.dimensions || (item.type === 'video' ? '4K 16:9' : item.type)}
                </p>
              </div>

              <div className="pt-2 border-t border-[#1F2937]/70 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  {item.destinations.map((dest) => (
                    <span key={dest} className="w-5 h-5 rounded-md bg-[#161B26] border border-[#1F2937] flex items-center justify-center">
                      {getPlatformIcon(dest)}
                    </span>
                  ))}
                </div>

                <Link
                  href={`/repurpose?id=${item.id}`}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-600/20 hover:bg-indigo-600 border border-indigo-500/30 hover:border-indigo-500 text-indigo-300 hover:text-white text-[11px] font-medium transition-all"
                >
                  <Sparkles className="w-3 h-3" />
                  <span>Repurpose</span>
                </Link>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Upload Modal */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-scaleUp">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white">Upload / Create Content</h3>
              <button onClick={() => setIsUploadModalOpen(false)} className="p-1 text-gray-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-300 block mb-1">Content Title</label>
                <input
                  type="text"
                  name="title"
                  required
                  placeholder="e.g. Masterclass on System Design"
                  className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-gray-300 block mb-1">Content Type</label>
                <select
                  name="type"
                  className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="video">Video (MP4, MOV, MKV)</option>
                  <option value="carousel">Carousel Deck</option>
                  <option value="image">Image (PNG, JPG, WebP)</option>
                  <option value="text">Text / Article Idea</option>
                </select>
              </div>

              <div className="border-2 border-dashed border-[#1F2937] hover:border-indigo-500/60 rounded-xl p-6 text-center transition-colors cursor-pointer bg-[#161B26]/40">
                <Upload className="w-6 h-6 text-indigo-400 mx-auto mb-2" />
                <p className="text-xs text-gray-300 font-medium">Drag & drop files or click to browse</p>
                <p className="text-[10px] text-gray-500 mt-1">Supports Video (up to 4GB), Images, PDFs</p>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsUploadModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-gray-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md transition-all"
                >
                  Upload Asset
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
