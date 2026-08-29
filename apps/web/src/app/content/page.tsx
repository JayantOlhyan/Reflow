"use client";

import React, { useState, useEffect, useRef } from 'react';
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
  FolderOpen,
  FileCode,
  AlertCircle,
  CheckCircle2,
  Play
} from 'lucide-react';
import { ContentItem } from '@/types';
import { YoutubeIcon, InstagramIcon, TiktokIcon, LinkedinIcon, XIcon } from '@/components/ui/SocialIcons';
import { api } from '@/lib/api';

export default function ContentLibraryPage() {
  const [activeTab, setActiveTab] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadMode, setUploadMode] = useState<'file' | 'text'>('file');
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<ContentItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadContent();
  }, [activeTab, searchQuery]);

  const loadContent = async () => {
    try {
      setLoading(true);
      const res = await api.getContentList({
        type: activeTab === 'draft' ? undefined : activeTab,
        status: activeTab === 'draft' ? 'DRAFT' : undefined,
        search: searchQuery || undefined
      });
      setItems(res.items || []);
      setTotalCount(res.total || 0);
    } catch (err) {
      console.warn("Failed to fetch content list:", err);
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'all', label: 'All' },
    { id: 'video', label: 'Videos' },
    { id: 'image', label: 'Images' },
    { id: 'pdf', label: 'PDFs' },
    { id: 'text', label: 'Text' },
    { id: 'draft', label: 'Drafts' },
  ];

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return null;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setUploadError(null);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setUploadError(null);
    setIsUploading(true);

    try {
      if (uploadMode === 'file') {
        if (!selectedFile) {
          throw new Error("Please select a file to upload.");
        }
        const formData = new FormData(e.currentTarget);
        const title = formData.get('title') as string;
        await api.uploadFile(selectedFile, title || selectedFile.name);
      } else {
        const formData = new FormData(e.currentTarget);
        const title = formData.get('textTitle') as string;
        const text = formData.get('textContent') as string;
        if (!text) throw new Error("Please enter text content.");
        await api.createTextContent(title || 'Untitled Note', text);
      }

      setIsUploadModalOpen(false);
      setSelectedFile(null);
      await loadContent();
    } catch (err: any) {
      setUploadError(err.message || "Upload failed. Please verify format and size.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this asset? Physical files will be removed.")) return;
    try {
      await api.deleteContent(id);
      setItems(items.filter(item => item.id !== id));
      setTotalCount(prev => Math.max(0, prev - 1));
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const renderAssetThumbnail = (item: ContentItem) => {
    const primaryAsset = item.assets && item.assets[0];
    const assetUrl = primaryAsset ? api.getAssetUrl(item.id, primaryAsset.id) : null;
    const cType = (item.content_type || item.type || '').toUpperCase();

    if (cType === 'IMAGE' && assetUrl) {
      return (
        <img
          src={assetUrl}
          alt={item.title}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
        />
      );
    }

    if (cType === 'VIDEO') {
      return (
        <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-br from-[#161B26] via-[#111827] to-[#0B0D12] text-gray-400 group-hover:text-indigo-400 transition-colors relative">
          <div className="w-10 h-10 rounded-full bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-300 group-hover:scale-110 transition-transform">
            <Play className="w-4 h-4 ml-0.5" />
          </div>
          {primaryAsset?.original_filename && (
            <span className="text-[10px] text-gray-500 font-mono mt-2 truncate max-w-[80%]">
              {primaryAsset.original_filename}
            </span>
          )}
        </div>
      );
    }

    if (cType === 'PDF') {
      return (
        <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-br from-[#1E1B4B]/50 via-[#111827] to-[#0B0D12] p-4 text-center">
          <FileText className="w-10 h-10 text-rose-400 mb-1" />
          <span className="text-[11px] font-semibold text-gray-300 truncate max-w-full">
            {primaryAsset?.original_filename || item.title}
          </span>
          <span className="text-[10px] text-gray-500 font-mono mt-0.5">Portable Document Format</span>
        </div>
      );
    }

    if (cType === 'TEXT') {
      return (
        <div className="w-full h-full flex flex-col justify-start bg-[#161B26]/80 p-4 font-mono text-[11px] text-gray-300 overflow-hidden leading-relaxed">
          <div className="flex items-center gap-1.5 text-cyan-400 font-bold mb-1">
            <FileCode className="w-3.5 h-3.5" />
            <span>NOTE / TEXT</span>
          </div>
          <p className="line-clamp-4 text-gray-400 text-[10px]">
            {item.text_content || 'Plain text content record.'}
          </p>
        </div>
      );
    }

    return (
      <div className="w-full h-full flex items-center justify-center bg-[#161B26]">
        <Layers className="w-8 h-8 text-gray-600" />
      </div>
    );
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Header & Main Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Content Library</h1>
          <p className="text-xs text-gray-400 mt-0.5">Real ingested source media, documents, and notes.</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setSelectedFile(null);
              setUploadError(null);
              setIsUploadModalOpen(true);
            }}
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

          <button onClick={loadContent} className="p-2 text-gray-400 hover:text-white rounded-xl bg-[#111827] border border-[#1F2937] hover:bg-[#161B26] transition-colors">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Grid or Empty State */}
      {loading ? (
        <div className="py-20 text-center text-xs text-gray-500 flex items-center justify-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
          <span>Loading content library from database...</span>
        </div>
      ) : items.length === 0 ? (
        <div className="py-20 text-center bg-[#111827]/40 border border-dashed border-[#1F2937] rounded-2xl p-8 space-y-3">
          <FolderOpen className="w-10 h-10 text-gray-600 mx-auto" />
          <h3 className="text-sm font-semibold text-white">No content items found</h3>
          <p className="text-xs text-gray-400 max-w-sm mx-auto">
            {searchQuery ? "No assets match your search criteria." : "Your repository is currently empty. Upload your first real video, image, PDF, or text note to begin."}
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
          {items.map((item) => {
            const primaryAsset = item.assets && item.assets[0];
            const cType = (item.content_type || item.type || '').toUpperCase();
            return (
              <div
                key={item.id}
                className="group bg-[#111827]/90 border border-[#1F2937] hover:border-indigo-500/50 rounded-2xl overflow-hidden transition-all duration-200 flex flex-col hover:shadow-xl hover:shadow-indigo-500/5"
              >
                <div className="relative aspect-[16/10] bg-[#161B26] overflow-hidden">
                  {renderAssetThumbnail(item)}
                  <div className="absolute inset-0 bg-gradient-to-t from-[#0B0D12]/90 via-transparent to-transparent pointer-events-none" />

                  <div className="absolute top-2.5 left-2.5 flex items-center gap-1.5 bg-[#0B0D12]/80 backdrop-blur-md px-2 py-1 rounded-lg border border-white/10 text-[10px] font-semibold text-gray-200">
                    {cType === 'VIDEO' && <Video className="w-3 h-3 text-red-400" />}
                    {cType === 'IMAGE' && <ImageIcon className="w-3 h-3 text-emerald-400" />}
                    {cType === 'PDF' && <FileText className="w-3 h-3 text-rose-400" />}
                    {cType === 'TEXT' && <FileCode className="w-3 h-3 text-cyan-400" />}
                    <span className="capitalize">{cType.toLowerCase()}</span>
                  </div>

                  <button
                    onClick={() => handleDelete(item.id)}
                    title="Delete Asset"
                    className="absolute top-2.5 right-2.5 p-1 rounded-lg bg-black/60 hover:bg-rose-600 text-gray-300 hover:text-white transition-colors opacity-0 group-hover:opacity-100"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>

                  <div className="absolute bottom-2.5 right-2.5 bg-[#0B0D12]/90 backdrop-blur-md px-2 py-0.5 rounded text-[10px] font-medium text-gray-300">
                    {primaryAsset?.file_size ? formatFileSize(primaryAsset.file_size) : item.status}
                  </div>
                </div>

                <div className="p-4 flex-1 flex flex-col justify-between space-y-3">
                  <div>
                    <h3 className="text-xs font-semibold text-white line-clamp-1 group-hover:text-indigo-300 transition-colors">
                      {item.title}
                    </h3>
                    <p className="text-[11px] text-gray-400 mt-1 truncate">
                      {primaryAsset?.original_filename || item.id}
                    </p>
                  </div>

                  <div className="pt-2 border-t border-[#1F2937]/70 flex items-center justify-between">
                    <span className="text-[10px] text-gray-500 font-mono">
                      {item.created_at ? new Date(item.created_at).toLocaleDateString() : 'Persisted'}
                    </span>

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
            );
          })}
        </div>
      )}

      {/* Upload Modal */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-scaleUp">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white">Ingest Real Content Asset</h3>
              <button onClick={() => setIsUploadModalOpen(false)} className="p-1 text-gray-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Ingestion Mode Toggle */}
            <div className="flex items-center gap-2 p-1 bg-[#161B26] rounded-xl border border-[#1F2937]">
              <button
                type="button"
                onClick={() => setUploadMode('file')}
                className={`flex-1 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  uploadMode === 'file' ? 'bg-indigo-600 text-white shadow-sm' : 'text-gray-400 hover:text-white'
                }`}
              >
                File Upload (Video, Image, PDF)
              </button>
              <button
                type="button"
                onClick={() => setUploadMode('text')}
                className={`flex-1 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  uploadMode === 'text' ? 'bg-indigo-600 text-white shadow-sm' : 'text-gray-400 hover:text-white'
                }`}
              >
                Text / Markdown Note
              </button>
            </div>

            {uploadError && (
              <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-3 text-xs text-rose-400 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{uploadError}</span>
              </div>
            )}

            <form onSubmit={handleUploadSubmit} className="space-y-4">
              {uploadMode === 'file' ? (
                <>
                  <div>
                    <label className="text-xs font-medium text-gray-300 block mb-1">Asset Title (Optional)</label>
                    <input
                      type="text"
                      name="title"
                      placeholder="e.g. Masterclass Video 01"
                      className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    accept=".mp4,.mov,.webm,.mkv,.png,.jpg,.jpeg,.webp,.pdf,.txt,.md"
                    className="hidden"
                  />

                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className="border-2 border-dashed border-[#1F2937] hover:border-indigo-500/60 rounded-xl p-6 text-center transition-colors cursor-pointer bg-[#161B26]/40"
                  >
                    <Upload className="w-6 h-6 text-indigo-400 mx-auto mb-2" />
                    {selectedFile ? (
                      <div className="space-y-1">
                        <p className="text-xs font-semibold text-emerald-400 flex items-center justify-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>{selectedFile.name}</span>
                        </p>
                        <p className="text-[10px] text-gray-400 font-mono">
                          {formatFileSize(selectedFile.size)} • {selectedFile.type || 'Binary'}
                        </p>
                      </div>
                    ) : (
                      <>
                        <p className="text-xs text-gray-300 font-medium">Click to choose a real file from disk</p>
                        <p className="text-[10px] text-gray-500 mt-1">MP4, MOV, PNG, JPG, PDF, TXT (up to 500MB)</p>
                      </>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="text-xs font-medium text-gray-300 block mb-1">Title</label>
                    <input
                      type="text"
                      name="textTitle"
                      required
                      placeholder="e.g. Content Repurposing Strategies"
                      className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium text-gray-300 block mb-1">Text / Markdown Body</label>
                    <textarea
                      name="textContent"
                      rows={5}
                      required
                      placeholder="Write or paste your article, transcript, or ideas here..."
                      className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl p-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 font-mono"
                    />
                  </div>
                </>
              )}

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
                  disabled={isUploading}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md transition-all disabled:opacity-50 flex items-center gap-1.5"
                >
                  {isUploading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>{isUploading ? "Uploading & Persisting..." : "Save Content"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
