"use client";

import React, { useState, useEffect } from 'react';
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
  X,
  Trash2,
  RefreshCw,
  FolderOpen
} from 'lucide-react';
import { ContentItem, ContentType } from '@/types';
import { YoutubeIcon, InstagramIcon, TiktokIcon, LinkedinIcon, XIcon } from '@/components/ui/SocialIcons';
import { api } from '@/lib/api';

export default function ContentLibraryPage() {
  const [activeTab, setActiveTab] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<ContentItem[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    loadContent();
  }, []);

  const loadContent = async () => {
    try {
      setLoading(true);
      const data = await api.getContentList();
      setItems(data);
    } catch (err) {
      console.warn("Failed to fetch content list:", err);
    } finally {
      setLoading(false);
    }
  };

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

  const handleUploadSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const title = formData.get('title') as string;
    const type = formData.get('type') as ContentType;

    try {
      setIsSubmitting(true);
      const newItem = await api.createContent({
        title: title || 'New Content Asset',
        type: type || 'video',
        thumbnail: 'https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=600&auto=format&fit=crop&q=80',
        duration: type === 'video' ? 180 : undefined,
        slide_count: type === 'carousel' ? 5 : undefined,
        status: 'draft',
        destinations: ['instagram', 'youtube']
      });

      setItems([newItem, ...items]);
      setIsUploadModalOpen(false);
    } catch (err: any) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this asset?")) return;
    try {
      await api.deleteContent(id);
      setItems(items.filter(item => item.id !== id));
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
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

      {/* Grid or Empty State */}
      {loading ? (
        <div className="py-20 text-center text-xs text-gray-500 flex items-center justify-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
          <span>Loading content library...</span>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="py-20 text-center bg-[#111827]/40 border border-dashed border-[#1F2937] rounded-2xl p-8 space-y-3">
          <FolderOpen className="w-10 h-10 text-gray-600 mx-auto" />
          <h3 className="text-sm font-semibold text-white">No content items found</h3>
          <p className="text-xs text-gray-400 max-w-sm mx-auto">
            {searchQuery ? "No assets match your search criteria." : "Your library is currently empty. Upload your first video, image, carousel, or text draft to begin."}
          </p>
          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md transition-all mt-2"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload First Asset</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {filteredItems.map((item) => (
            <div
              key={item.id}
              className="group bg-[#111827]/90 border border-[#1F2937] hover:border-indigo-500/50 rounded-2xl overflow-hidden transition-all duration-200 flex flex-col hover:shadow-xl hover:shadow-indigo-500/5"
            >
              <div className="relative aspect-[16/10] bg-[#161B26] overflow-hidden">
                <img
                  src={item.thumbnail || 'https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=600&auto=format&fit=crop&q=80'}
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

                <button
                  onClick={() => handleDelete(item.id)}
                  className="absolute top-2.5 right-2.5 p-1 rounded-lg bg-black/60 hover:bg-rose-600/80 text-gray-300 hover:text-white transition-colors opacity-0 group-hover:opacity-100"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>

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
                    {item.created_at || 'Recently'} • {item.dimensions || (item.type === 'video' ? '16:9' : item.type)}
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
      )}

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
                <p className="text-[10px] text-gray-500 mt-1">Supports Video (up to 500MB), Images, PDFs</p>
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
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md transition-all disabled:opacity-50"
                >
                  {isSubmitting ? "Creating..." : "Upload Asset"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
