"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { ShieldCheck, Check, X, AlertTriangle, CheckSquare, Square, Layers, RefreshCw, Filter, AlertCircle } from 'lucide-react';
import { PublicationItem } from '@/types';
import { api } from '@/lib/api';

export default function ApprovalsPage() {
  const [publications, setPublications] = useState<PublicationItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isBulkConfirmOpen, setIsBulkConfirmOpen] = useState<boolean>(false);
  const [isApproving, setIsApproving] = useState<boolean>(false);
  const [filterPlatform, setFilterPlatform] = useState<string>('all');

  useEffect(() => {
    loadApprovals();
  }, [filterPlatform]);

  const loadApprovals = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getPublications();
      let items = res.items || [];

      // Filter to items needing review/approval (DRAFT or SCHEDULED)
      items = items.filter(p => p.status === 'DRAFT' || p.status === 'SCHEDULED' || p.error_code === 'GOVERNANCE_WARNING');
      if (filterPlatform !== 'all') {
        items = items.filter(p => p.platform.toLowerCase() === filterPlatform.toLowerCase());
      }
      setPublications(items);
      setSelectedIds([]);
    } catch (err: any) {
      setError(err.message || "Failed to load approval items");
    } finally {
      setLoading(false);
    }
  };

  const handleToggleSelect = (id: string) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
  };

  const handleSelectAll = () => {
    if (selectedIds.length === publications.length) {
      setSelectedIds([]);
    } else {
      // Filter out any BLOCKED items from bulk selection
      const safeIds = publications.filter(p => p.error_code !== 'GOVERNANCE_BLOCKED').map(p => p.id);
      setSelectedIds(safeIds);
    }
  };

  const handleSingleApprove = async (pubId: string) => {
    try {
      setIsApproving(true);
      await api.approvePublication(pubId);
      setPublications(prev => prev.filter(p => p.id !== pubId));
      setSelectedIds(prev => prev.filter(i => i !== pubId));
    } catch (e: any) {
      alert(`Approval failed: ${e.message}`);
    } finally {
      setIsApproving(false);
    }
  };

  const handleBulkApprove = async () => {
    if (selectedIds.length === 0) return;
    try {
      setIsApproving(true);
      const res = await api.approveBatchPublications(selectedIds);
      setIsBulkConfirmOpen(false);
      loadApprovals();
    } catch (e: any) {
      alert(`Bulk approval failed: ${e.message}`);
    } finally {
      setIsApproving(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-emerald-400" />
            <h1 className="text-2xl font-bold text-white tracking-tight">Centralized Approval Center</h1>
          </div>
          <p className="text-xs text-slate-400">
            Review and sign off on pending content, clips, carousels, and scheduled publications before release.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {selectedIds.length > 0 && (
            <button
              onClick={() => setIsBulkConfirmOpen(true)}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-emerald-600/20 transition flex items-center gap-1.5"
            >
              <Check className="w-4 h-4" />
              <span>Approve ({selectedIds.length})</span>
            </button>
          )}

          <button
            onClick={loadApprovals}
            className="p-2 text-slate-400 hover:text-white bg-slate-800 border border-slate-700 rounded-xl text-xs flex items-center gap-1"
            title="Refresh list"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center justify-between bg-slate-900 border border-slate-800 rounded-2xl p-4">
        <div className="flex items-center space-x-2 text-xs">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-slate-400 font-medium">Filter Platform:</span>
          {['all', 'linkedin', 'instagram', 'x', 'youtube'].map(plat => (
            <button
              key={plat}
              onClick={() => setFilterPlatform(plat)}
              className={`px-3 py-1 rounded-lg uppercase font-semibold text-[11px] transition ${
                filterPlatform === plat
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {plat}
            </button>
          ))}
        </div>

        {publications.length > 0 && (
          <button
            onClick={handleSelectAll}
            className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5"
          >
            {selectedIds.length === publications.length ? (
              <CheckSquare className="w-4 h-4 text-indigo-400" />
            ) : (
              <Square className="w-4 h-4 text-slate-500" />
            )}
            <span>Select All Safe Items</span>
          </button>
        )}
      </div>

      {/* Approval List */}
      {loading ? (
        <div className="py-16 text-center text-slate-500 text-sm">Loading approval queue...</div>
      ) : error ? (
        <div className="py-12 text-center text-rose-400 text-sm">{error}</div>
      ) : publications.length === 0 ? (
        <div className="py-20 text-center bg-slate-900 border border-slate-800 rounded-2xl p-8">
          <ShieldCheck className="w-12 h-12 text-emerald-500/40 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-white">All Clear!</h3>
          <p className="text-xs text-slate-400 mt-1">No publications currently pending review or approval.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {publications.map((pub) => {
            const isSelected = selectedIds.includes(pub.id);
            const isBlocked = pub.error_code === 'GOVERNANCE_BLOCKED';

            return (
              <div
                key={pub.id}
                className={`p-4 rounded-2xl border transition flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                  isSelected ? 'bg-indigo-900/10 border-indigo-500/40' : 'bg-slate-900 border-slate-800'
                }`}
              >
                <div className="flex items-start gap-3 min-w-0">
                  <button
                    disabled={isBlocked}
                    onClick={() => handleToggleSelect(pub.id)}
                    className="mt-1 text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    {isSelected ? <CheckSquare className="w-5 h-5 text-indigo-400" /> : <Square className="w-5 h-5 text-slate-600" />}
                  </button>

                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-0.5 text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded uppercase">
                        {pub.platform}
                      </span>
                      <span className="text-xs font-semibold text-white truncate">
                        {pub.title || `Publication ${pub.id}`}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 line-clamp-2">{pub.description || "No description provided."}</p>
                    
                    {pub.scheduled_at && (
                      <div className="text-[11px] text-slate-500 font-mono">
                        Scheduled for: {new Date(pub.scheduled_at).toLocaleString()}
                      </div>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 self-end md:self-center">
                  <Link
                    href={`/content/${pub.content_id}`}
                    className="px-3 py-1.5 text-xs text-slate-400 hover:text-white bg-slate-800 rounded-lg hover:bg-slate-750 transition"
                  >
                    Inspect Source
                  </Link>

                  <button
                    disabled={isApproving || isBlocked}
                    onClick={() => handleSingleApprove(pub.id)}
                    className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold disabled:opacity-50 transition flex items-center gap-1"
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>Approve</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Bulk Approval Confirmation Modal */}
      {isBulkConfirmOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full space-y-4">
            <h3 className="text-lg font-semibold text-white">Approve Multiple Items</h3>
            <p className="text-xs text-slate-300">
              Are you sure you want to approve <strong className="text-emerald-400">{selectedIds.length}</strong> selected items for publishing?
            </p>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setIsBulkConfirmOpen(false)}
                className="px-4 py-2 text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                disabled={isApproving}
                onClick={handleBulkApprove}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold"
              >
                {isApproving ? "Approving..." : `Approve ${selectedIds.length} Items`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
