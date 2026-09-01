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
  ArrowRight
} from 'lucide-react';
import { api } from '@/lib/api';
import { PublicationItem, NotificationItem } from '@/types';

export default function OverviewPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [overview, setOverview] = useState<{
    metrics: { total: number; published: number; scheduled: number; failed: number };
    recent_activity: any[];
  }>({
    metrics: { total: 0, published: 0, scheduled: 0, failed: 0 },
    recent_activity: []
  });

  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [publications, setPublications] = useState<PublicationItem[]>([]);

  useEffect(() => {
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
        setError("Unable to connect to Reflow API server.");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const metrics = overview.metrics;

  // Needs Attention items
  const failedPubs = publications.filter(p => p.status === 'FAILED' || p.status === 'REAUTH_REQUIRED');
  const pendingApprovals = publications.filter(p => p.status === 'DRAFT' || p.error_code === 'GOVERNANCE_WARNING');
  const errorNotifs = notifications.filter(n => n.severity === 'ERROR' || n.severity === 'WARNING');

  const upcomingScheduled = publications.filter(p => p.status === 'SCHEDULED').slice(0, 5);

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Greeting & Primary CTA */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-white tracking-tight flex items-center gap-2">
            Workspace Overview <span className="inline-block">⚡</span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Real-time status of your content pipeline, publication dispatches, and system attention items.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/repurpose"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-lg shadow-indigo-500/25 transition-all"
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

      {/* NEEDS ATTENTION SECTION (Action-Oriented Queue) */}
      {(failedPubs.length > 0 || pendingApprovals.length > 0 || errorNotifs.length > 0) && (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-rose-300 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-rose-400" />
              <span>Needs Attention ({failedPubs.length + pendingApprovals.length})</span>
            </h2>
            <Link href="/approvals" className="text-xs font-medium text-rose-400 hover:underline">
              Open Approvals & Fixes →
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {failedPubs.map(p => (
              <div key={p.id} className="p-3.5 bg-slate-900/90 rounded-xl border border-rose-500/30 flex items-center justify-between text-xs">
                <div>
                  <span className="font-bold text-white uppercase">{p.platform}</span>: <span className="text-slate-300">{p.title || p.id}</span>
                  <div className="text-rose-400 text-[11px] mt-0.5">{p.error_message || "Publishing failed."}</div>
                </div>
                <Link href={`/publishing?id=${p.id}`} className="px-3 py-1 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 rounded-lg font-medium whitespace-nowrap">
                  Retry →
                </Link>
              </div>
            ))}

            {pendingApprovals.map(p => (
              <div key={p.id} className="p-3.5 bg-slate-900/90 rounded-xl border border-amber-500/30 flex items-center justify-between text-xs">
                <div>
                  <span className="font-bold text-amber-300 uppercase">{p.platform}</span>: <span className="text-slate-300">{p.title || p.id}</span>
                  <div className="text-amber-400/80 text-[11px] mt-0.5">Awaiting sign-off</div>
                </div>
                <Link href="/approvals" className="px-3 py-1 bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 rounded-lg font-medium whitespace-nowrap">
                  Approve →
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 font-medium">Total Content Items</div>
          <div className="text-2xl font-bold text-white">{metrics.total}</div>
        </div>
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 font-medium">Published Posts</div>
          <div className="text-2xl font-bold text-emerald-400">{metrics.published}</div>
        </div>
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 font-medium">Scheduled Queue</div>
          <div className="text-2xl font-bold text-indigo-400">{metrics.scheduled}</div>
        </div>
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 font-medium">Failed Dispatches</div>
          <div className="text-2xl font-bold text-rose-400">{metrics.failed}</div>
        </div>
      </div>

      {/* Upcoming Schedule & Quick Links Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Upcoming Queue */}
        <div className="lg:col-span-8 bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <Calendar className="w-4 h-4 text-indigo-400" />
              <span>Upcoming Scheduled Dispatches</span>
            </h3>
            <Link href="/calendar" className="text-xs text-indigo-400 hover:underline">View Calendar →</Link>
          </div>

          {upcomingScheduled.length === 0 ? (
            <div className="py-10 text-center text-xs text-slate-500">No upcoming posts scheduled.</div>
          ) : (
            <div className="space-y-2">
              {upcomingScheduled.map(p => (
                <div key={p.id} className="p-3 bg-slate-850 rounded-xl border border-slate-800 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-3">
                    <span className="px-2 py-0.5 text-[10px] font-bold bg-purple-500/20 text-purple-300 rounded uppercase">
                      {p.platform}
                    </span>
                    <span className="font-medium text-white">{p.title || p.id}</span>
                  </div>
                  <span className="text-slate-400 font-mono text-[11px]">
                    {p.scheduled_at ? new Date(p.scheduled_at).toLocaleString() : 'Pending'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Smart Recommendations */}
        <div className="lg:col-span-4 bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-amber-400" />
            <span>Smart Shortcuts</span>
          </h3>

          <div className="space-y-3">
            <Link
              href="/repurpose"
              className="p-3.5 rounded-xl bg-slate-850/80 hover:bg-indigo-600/10 border border-slate-800 hover:border-indigo-500/40 transition block group"
            >
              <div className="text-xs font-semibold text-white group-hover:text-indigo-300">Extract Viral Clips</div>
              <div className="text-[11px] text-slate-400 mt-0.5">Turn long-form video into high-retention clips.</div>
            </Link>

            <Link
              href="/carousel"
              className="p-3.5 rounded-xl bg-slate-850/80 hover:bg-purple-600/10 border border-slate-800 hover:border-purple-500/40 transition block group"
            >
              <div className="text-xs font-semibold text-white group-hover:text-purple-300">Design Multi-Slide Deck</div>
              <div className="text-[11px] text-slate-400 mt-0.5">Generate PDF carousels for LinkedIn & Instagram.</div>
            </Link>

            <Link
              href="/intelligence"
              className="p-3.5 rounded-xl bg-slate-850/80 hover:bg-amber-600/10 border border-slate-800 hover:border-amber-500/40 transition block group"
            >
              <div className="text-xs font-semibold text-white group-hover:text-amber-300">Content Intelligence</div>
              <div className="text-[11px] text-slate-400 mt-0.5">Discover content gaps and hook recommendations.</div>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
