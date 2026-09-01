"use client";

import React, { useState } from 'react';
import { X, Video, Image as ImageIcon, FileText, Scissors, Layers, Upload, AlertCircle } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';

interface QuickCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function QuickCreateModal({ isOpen, onClose }: QuickCreateModalProps) {
  const [activeMode, setActiveMode] = useState<'menu' | 'upload_file' | 'add_text'>('menu');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [textTitle, setTextTitle] = useState('');
  const [textContent, setTextContent] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  if (!isOpen) return null;

  const handleFileUpload = async () => {
    if (!selectedFile) return;
    try {
      setIsUploading(true);
      setError(null);
      const res = await api.uploadFile(selectedFile);
      onClose();
      router.push(`/content/${res.id}`);
    } catch (e: any) {
      setError(e.message || "Upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  const handleTextUpload = async () => {
    if (!textTitle.trim() || !textContent.trim()) return;
    try {
      setIsUploading(true);
      setError(null);
      const res = await api.createTextContent(textTitle, textContent);
      onClose();
      router.push(`/content/${res.id}`);
    } catch (e: any) {
      setError(e.message || "Failed to create text note");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/70 backdrop-blur-sm p-4 flex justify-center items-center">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">Create New Content</h3>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-white rounded-md">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5">
          {error && (
            <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {activeMode === 'menu' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                onClick={() => setActiveMode('upload_file')}
                className="p-4 rounded-xl border border-slate-800 bg-slate-850/60 hover:bg-indigo-600/10 hover:border-indigo-500/40 text-left transition group"
              >
                <div className="p-2.5 rounded-lg bg-indigo-500/20 text-indigo-400 w-fit mb-3 group-hover:scale-105 transition-transform">
                  <Video className="w-5 h-5" />
                </div>
                <h4 className="text-sm font-semibold text-white">Upload Media</h4>
                <p className="text-xs text-slate-400 mt-1">Video (MP4, MOV), Image, or PDF</p>
              </button>

              <button
                onClick={() => setActiveMode('add_text')}
                className="p-4 rounded-xl border border-slate-800 bg-slate-850/60 hover:bg-blue-600/10 hover:border-blue-500/40 text-left transition group"
              >
                <div className="p-2.5 rounded-lg bg-blue-500/20 text-blue-400 w-fit mb-3 group-hover:scale-105 transition-transform">
                  <FileText className="w-5 h-5" />
                </div>
                <h4 className="text-sm font-semibold text-white">Add Text Note</h4>
                <p className="text-xs text-slate-400 mt-1">Direct script, post draft, or markdown</p>
              </button>

              <button
                onClick={() => { onClose(); router.push('/repurpose'); }}
                className="p-4 rounded-xl border border-slate-800 bg-slate-850/60 hover:bg-emerald-600/10 hover:border-emerald-500/40 text-left transition group"
              >
                <div className="p-2.5 rounded-lg bg-emerald-500/20 text-emerald-400 w-fit mb-3 group-hover:scale-105 transition-transform">
                  <Scissors className="w-5 h-5" />
                </div>
                <h4 className="text-sm font-semibold text-white">Generate Clips</h4>
                <p className="text-xs text-slate-400 mt-1">Extract viral clips from existing video</p>
              </button>

              <button
                onClick={() => { onClose(); router.push('/carousel'); }}
                className="p-4 rounded-xl border border-slate-800 bg-slate-850/60 hover:bg-purple-600/10 hover:border-purple-500/40 text-left transition group"
              >
                <div className="p-2.5 rounded-lg bg-purple-500/20 text-purple-400 w-fit mb-3 group-hover:scale-105 transition-transform">
                  <Layers className="w-5 h-5" />
                </div>
                <h4 className="text-sm font-semibold text-white">Generate Carousel</h4>
                <p className="text-xs text-slate-400 mt-1">Design multi-slide PDF/PNG carousel</p>
              </button>
            </div>
          ) : activeMode === 'upload_file' ? (
            <div className="space-y-4">
              <div className="border-2 border-dashed border-slate-750 hover:border-indigo-500/50 rounded-xl p-8 text-center bg-slate-850/40 transition">
                <input
                  type="file"
                  id="quick-file-input"
                  className="hidden"
                  accept="video/*,image/*,application/pdf"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                />
                <label htmlFor="quick-file-input" className="cursor-pointer">
                  <Upload className="w-10 h-10 mx-auto text-indigo-400 mb-2 opacity-80" />
                  <p className="text-sm font-medium text-white">
                    {selectedFile ? selectedFile.name : "Click to choose video, image, or PDF"}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">Max file size: 500 MB</p>
                </label>
              </div>

              <div className="flex justify-between items-center pt-2">
                <button
                  type="button"
                  onClick={() => setActiveMode('menu')}
                  className="px-4 py-2 text-xs text-slate-400 hover:text-white"
                >
                  ← Back
                </button>
                <button
                  type="button"
                  disabled={!selectedFile || isUploading}
                  onClick={handleFileUpload}
                  className="px-5 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl disabled:opacity-50 transition"
                >
                  {isUploading ? "Uploading..." : "Upload Content"}
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Title</label>
                <input
                  type="text"
                  value={textTitle}
                  onChange={(e) => setTextTitle(e.target.value)}
                  placeholder="e.g. 5 Content Strategy Principles for 2026"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Content Body</label>
                <textarea
                  rows={5}
                  value={textContent}
                  onChange={(e) => setTextContent(e.target.value)}
                  placeholder="Write or paste your script, note, or article text here..."
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-between items-center pt-2">
                <button
                  type="button"
                  onClick={() => setActiveMode('menu')}
                  className="px-4 py-2 text-xs text-slate-400 hover:text-white"
                >
                  ← Back
                </button>
                <button
                  type="button"
                  disabled={!textTitle.trim() || !textContent.trim() || isUploading}
                  onClick={handleTextUpload}
                  className="px-5 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl disabled:opacity-50 transition"
                >
                  {isUploading ? "Creating..." : "Save Text Content"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
