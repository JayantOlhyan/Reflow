"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  Sparkles, 
  ArrowUpRight, 
  Layers, 
  Clock, 
  AlertTriangle, 
  CheckCircle2, 
  TrendingUp,
  Plus,
  RefreshCw,
  FolderOpen,
  ShieldCheck,
  Calendar,
  Lightbulb,
  ArrowRight,
  Activity,
  Share2
} from 'lucide-react';
import { api } from '@/lib/api';
import { PublicationItem, NotificationItem } from '@/types';
import { ErrorDiagnosticModal } from '@/components/ui/ErrorDiagnosticModal';

export default function OverviewPage() {
  const [loading, setLoading] = useState(true);
  const [errorModal, setErrorModal] = useState<{ open: boolean; message: string; tech?: string }>({
    open: false,
    message: ''
  });
  const [overview, setOverview] = useState<{
    metrics: { total: number; published: number; scheduled: number; failed: number };
    recent_activity: any[];
  }>({
    metrics: { total: 0, published: 0, scheduled: 0, failed: 0 },
    recent_activity: []
  });

  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [publications, setPublications] = useState<PublicationItem[]>([]);

  async function loadData() {
    try {
      setLoading(true);
      const [data, notifRes, pubRes] = await Promise.all([
        api.getOverview(),
        api.getNotifications(10),
        api.getPublications()
      ]);
      setOverview(data);
      setNotifications(notifRes.items || []);
      setPublications(pubRes.items || []);
    } catch (err: any) {
      console.warn("Could not load overview from server:", err);
      setErrorModal({
        open: true,
        message: "Unable to connect to Reflow API server. Processing queue metrics could not be retrieved.",
        tech: err.message || String(err)
      });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const metrics = overview.metrics;
  const failedPubs = publications.filter(p => p.status === 'FAILED' || p.status === 'REAUTH_REQUIRED');
  const pendingApprovals = publications.filter(p => p.status === 'DRAFT' || p.error_code === 'GOVERNANCE_WARNING');
  const upcomingScheduled = publications.filter(p => p.status === 'SCHEDULED').slice(0, 5);
  const recentPublished = publications.filter(p => p.status === 'PUBLISHED').slice(0, 5);

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Error Diagnostic Modal */}
      <ErrorDiagnosticModal
        isOpen={errorModal.open}
        onClose={() => setErrorModal({ open: false, message: '' })}
        onRetry={loadData}
        title="Dashboard Sync Failed"
        userMessage={errorModal.message}
        technicalError={errorModal.tech}
      />

      {/* Header & Quick Action Launcher */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-[#1F2937]/70 pb-5">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-white tracking-tight flex items-center gap-2">
            Overview <span className="inline-block text-indigo-400">⚡</span>
          </h1>
          <p className="text-xs md:text-sm text-gray-400 mt-1">
            Real-time status of your content pipeline, scheduled publications, and system health.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/repurpose"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-lg shadow-indigo-500/25 transition-all"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Repurpose Media</span>
          </Link>
          <Link
            href="/content"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#161B26] hover:bg-[#1F2937] border border-[#1F2937] text-gray-200 text-xs font-semibold transition-all"
          >
            <FolderOpen className="w-3.5 h-3.5" />
            <span>Content Library</span>
          </Link>
        </div>
      </div>

      {/* 1. WHAT IS HAPPENING? (Live Operational Status) */}
      <div className="space-y-4">
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2">
          <Activity className="w-4 h-4 text-indigo-400" />
          <span>1. What Is Happening?</span>
        </h2>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-5 rounded-2xl bg-[#11141D] border border-[#1F2937] space-y-1">
            <div className="text-xs text-gray-400 font-medium">Content Items</div>
            <div className="text-2xl font-bold text-white">{metrics.total}</div>
          </div>
          <div className="p-5 rounded-2xl bg-[#11141D] border border-[#1F2937] space-y-1">
            <div className="text-xs text-gray-400 font-medium">Published</div>
            <div className="text-2xl font-bold text-emerald-400">{metrics.published}</div>
          </div>
          <div className="p-5 rounded-2xl bg-[#11141D] border border-[#1F2937] space-y-1">
            <div className="text-xs text-gray-400 font-medium">Scheduled Queue</div>
            <div className="text-2xl font-bold text-indigo-400">{metrics.scheduled}</div>
          </div>
          <div className="p-5 rounded-2xl bg-[#11141D] border border-[#1F2937] space-y-1">
            <div className="text-xs text-gray-400 font-medium">Failed Dispatches</div>
            <div className="text-2xl font-bold text-rose-400">{metrics.failed}</div>
          </div>
        </div>

        {/* Needs Attention Warning Callout */}
        {(failedPubs.length > 0 || pendingApprovals.length > 0) && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-2xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-rose-300 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400" />
                <span>Needs Attention ({failedPubs.length + pendingApprovals.length})</span>
              </h3>
              <Link href="/approvals" className="text-xs font-medium text-rose-400 hover:underline">
                Review Approvals →
              </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {failedPubs.map(p => (
                <div key={p.id} className="p-3 bg-[#0B0D12] rounded-xl border border-rose-500/30 flex items-center justify-between text-xs">
                  <div>
                    <span className="font-bold text-white uppercase">{p.platform}</span>: <span className="text-gray-300">{p.title || p.id}</span>
                    <div className="text-rose-400 text-[11px] mt-0.5">{p.error_message || "Publishing failed."}</div>
                  </div>
                  <Link href={`/publishing?id=${p.id}`} className="px-3 py-1 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 rounded-lg font-medium whitespace-nowrap">
                    Retry →
                  </Link>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
