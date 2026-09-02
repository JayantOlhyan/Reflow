"use client";

import React, { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Layers, Search, RefreshCw, ExternalLink, RotateCcw, AlertTriangle, CheckCircle, Clock, XCircle, FileText } from 'lucide-react';
import { PublicationItem } from '@/types';
import { api } from '@/lib/api';

function PublishingContent() {
  const searchParams = useSearchParams();
  const highlightId = searchParams?.get('id');

  const [publications, setPublications] = useState<PublicationItem[]>([]);
  const [activeTab, setActiveTab] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedPub, setSelectedPub] = useState<PublicationItem | null>(null);
  const [isRetrying, setIsRetrying] = useState<boolean>(false);

  useEffect(() => {
    loadPublications();
  }, [activeTab]);

  useEffect(() => {
    if (highlightId && publications.length > 0) {
      const found = publications.find(p => p.id === highlightId);
      if (found) setSelectedPub(found);
    }
  }, [highlightId, publications]);

  const loadPublications = async () => {
    try {
      setLoading(true);
      const res = await api.getPublications();
      let items = res.items || [];

      if (activeTab !== 'all') {
        items = items.filter(p => p.status.toLowerCase() === activeTab.toLowerCase());
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        items = items.filter(p => (p.title || '').toLowerCase().includes(q) || (p.platform || '').toLowerCase().includes(q));
      }
      setPublications(items);
    } catch (e) {
      console.warn("Failed to load publications:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = async (pubId: string) => {
    try {
      setIsRetrying(true);
      const updated = await api.retryPublication(pubId);
      setPublications(prev => prev.map(p => p.id === pubId ? updated : p));
      setSelectedPub(updated);
    } catch (e: any) {
      alert(`Retry failed: ${e.message}`);
    } finally {
      setIsRetrying(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case 'PUBLISHED':
        return <span className="px-2.5 py-0.5 text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full">Published</span>;
      case 'PUBLISHING':
      case 'UPLOADING':
        return <span className="px-2.5 py-0.5 text-xs font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30 rounded-full animate-pulse">Publishing...</span>;
      case 'SCHEDULED':
        return <span className="px-2.5 py-0.5 text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded-full">Scheduled</span>;
      case 'FAILED':
        return <span className="px-2.5 py-0.5 text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30 rounded-full">Failed</span>;
      default:
        return <span className="px-2.5 py-0.5 text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700 rounded-full">{status}</span>;
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Layers className="w-6 h-6 text-indigo-400" />
            <h1 className="text-2xl font-bold text-white tracking-tight">Publishing Workspace</h1>
          </div>
          <p className="text-xs text-slate-400">
            Centralized queue monitoring real-time post lifecycle, scheduled dispatches, external links, and failed retries.
          </p>
        </div>

        <button
          onClick={loadPublications}
          className="p-2 text-slate-400 hover:text-white bg-slate-800 border border-slate-700 rounded-xl text-xs flex items-center gap-1.5 self-start sm:self-center"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Refresh Queue</span>
        </button>
      </div>

      {/* Tabs & Search */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-2">
        <div className="flex items-center space-x-2 overflow-x-auto">
          {[
            { id: 'all', label: 'All Posts' },
            { id: 'draft', label: 'Drafts' },
            { id: 'scheduled', label: 'Scheduled' },
            { id: 'publishing', label: 'Publishing' },
            { id: 'published', label: 'Published' },
            { id: 'failed', label: 'Failed' }
          ].map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-3.5 py-2 text-xs font-semibold rounded-xl transition ${
                activeTab === t.id
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="relative w-64">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by title or platform..."
            className="w-full bg-slate-850 border border-slate-750 rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Publications Table */}
      {loading ? (
        <div className="py-16 text-center text-slate-500 text-sm">Loading publishing queue...</div>
      ) : publications.length === 0 ? (
        <div className="py-20 text-center bg-slate-900 border border-slate-800 rounded-2xl p-8">
          <Layers className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-white">No Publications Found</h3>
          <p className="text-xs text-slate-400 mt-1">No post records match the selected status filter.</p>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-850/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="p-4">Platform & Title</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Scheduled For</th>
                  <th className="p-4">Published At</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {publications.map((pub) => (
                  <tr key={pub.id} className="hover:bg-slate-850/50 transition">
                    <td className="p-4">
                      <div className="flex items-center space-x-3">
                        <span className="px-2 py-0.5 text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded uppercase">
                          {pub.platform}
                        </span>
                        <div>
                          <div className="font-semibold text-white text-sm line-clamp-1">
                            {pub.title || `Publication ${pub.id}`}
                          </div>
                          <div className="text-[11px] text-slate-400 line-clamp-1">{pub.description}</div>
                        </div>
                      </div>
                    </td>
                    <td className="p-4">{getStatusBadge(pub.status)}</td>
                    <td className="p-4 text-slate-400 font-mono">
                      {pub.scheduled_at ? new Date(pub.scheduled_at).toLocaleString() : 'Immediate'}
                    </td>
                    <td className="p-4 text-slate-400 font-mono">
                      {pub.published_at ? new Date(pub.published_at).toLocaleString() : '—'}
                    </td>
                    <td className="p-4 text-right space-x-2">
                      <button
                        onClick={() => setSelectedPub(pub)}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-750 text-slate-200 rounded-lg font-medium transition"
                      >
                        Inspect
                      </button>
                      {pub.external_url && (
                        <a
                          href={pub.external_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-lg font-medium transition"
                        >
                          <span>Link</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Publication Detail Modal */}
      {selectedPub && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-lg w-full space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 text-xs font-bold bg-indigo-500/20 text-indigo-300 rounded uppercase">
                  {selectedPub.platform}
                </span>
                <h3 className="text-base font-semibold text-white">Publication Detail</h3>
              </div>
              <button onClick={() => setSelectedPub(null)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-500 text-[10px] uppercase font-mono">Title</label>
                <div className="text-sm font-semibold text-white mt-0.5">{selectedPub.title || "Untitled"}</div>
              </div>

              <div>
                <label className="text-slate-500 text-[10px] uppercase font-mono">Caption / Content</label>
                <div className="p-3 bg-slate-850 rounded-xl border border-slate-800 text-slate-300 leading-relaxed whitespace-pre-wrap mt-0.5">
                  {selectedPub.description || "No caption text."}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="text-slate-500 text-[10px] uppercase font-mono">Status</label>
                  <div className="mt-0.5">{getStatusBadge(selectedPub.status)}</div>
                </div>
                <div>
                  <label className="text-slate-500 text-[10px] uppercase font-mono">Attempts</label>
                  <div className="text-white font-mono mt-0.5">{selectedPub.attempt_count || 1}</div>
                </div>
              </div>

              {selectedPub.external_post_id && (
                <div>
                  <label className="text-slate-500 text-[10px] uppercase font-mono">External Post ID</label>
                  <div className="text-indigo-400 font-mono mt-0.5">{selectedPub.external_post_id}</div>
                </div>
              )}

              {selectedPub.error_message && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 space-y-1.5">
                  <div className="font-bold text-rose-400 flex items-center gap-1.5">
                    <AlertTriangle className="w-4 h-4" />
                    <span>Failure Explanation ({selectedPub.error_code || 'PUBLISH_ERROR'})</span>
                  </div>
                  <div className="text-xs leading-relaxed">{selectedPub.error_message}</div>
                </div>
              )}

              {/* Modal Actions */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button onClick={() => setSelectedPub(null)} className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white rounded-xl">
                  Close
                </button>
                {(selectedPub.status === 'FAILED' || selectedPub.status === 'REAUTH_REQUIRED') && (
                  <button
                    onClick={() => handleRetry(selectedPub.id)}
                    disabled={isRetrying}
                    className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-500 rounded-xl transition shadow-lg shadow-rose-600/20"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>{isRetrying ? 'Retrying...' : 'Retry Publication'}</span>
                  </button>
                )}
              </div>
            </div>

            <div className="flex justify-between items-center pt-4 border-t border-slate-800">
              <Link
                href={`/content/${selectedPub.content_id}`}
                onClick={() => setSelectedPub(null)}
                className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
              >
                Go to Source Content →
              </Link>

              <div className="flex items-center space-x-2">
                {selectedPub.status === 'FAILED' && (
                  <button
                    disabled={isRetrying}
                    onClick={() => handleRetry(selectedPub.id)}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>{isRetrying ? "Retrying..." : "Retry Post"}</span>
                  </button>
                )}
                <button
                  onClick={() => setSelectedPub(null)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-medium"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function PublishingWorkspacePage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-500">Loading publishing workspace...</div>}>
      <PublishingContent />
    </Suspense>
  );
}
