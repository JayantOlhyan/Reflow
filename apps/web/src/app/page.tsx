"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  Sparkles, 
  ArrowUpRight, 
  Layers, 
  Clock, 
  AlertCircle, 
  CheckCircle2, 
  TrendingUp,
  Plus,
  RefreshCw,
  FolderOpen
} from 'lucide-react';
import { YoutubeIcon, InstagramIcon, TiktokIcon, LinkedinIcon, XIcon } from '@/components/ui/SocialIcons';
import { api } from '@/lib/api';

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

  const [healthStatus, setHealthStatus] = useState<string>("checking");

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const data = await api.getOverview();
        setOverview(data);
        const health = await api.getSystemHealth();
        setHealthStatus(health.status);
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

  const statusBadge = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'published':
      case 'succeeded':
        return <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Published</span>;
      case 'processing':
      case 'running':
        return <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 animate-pulse">Processing</span>;
      case 'scheduled':
      case 'queued':
        return <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20">Queued</span>;
      case 'failed':
        return <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-rose-500/10 text-rose-400 border border-rose-500/20">Failed</span>;
      default:
        return <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-gray-700/50 text-gray-300">{status || 'Draft'}</span>;
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Greeting */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-white tracking-tight flex items-center gap-2">
            Good evening, Jayant <span className="inline-block animate-wave">👋</span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Here&apos;s what&apos;s happening with your content pipeline across connected platforms.
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
            href="/carousel"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#161B26] hover:bg-[#1F2937] border border-[#1F2937] text-gray-200 text-xs font-semibold transition-all"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create Carousel</span>
          </Link>
        </div>
      </div>

      {error && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 text-xs text-amber-300 flex items-center justify-between">
          <span>{error} Operating in offline mode.</span>
          <button onClick={() => window.location.reload()} className="underline font-semibold">Retry</button>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#111827]/80 backdrop-blur-sm border border-[#1F2937] rounded-2xl p-5 hover:border-indigo-500/40 transition-all group">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-xs font-medium uppercase tracking-wider">Total Content</span>
            <Layers className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white tracking-tight">{loading ? '...' : metrics.total}</span>
          </div>
          <span className="text-[11px] text-gray-500 mt-1 block">Assets in repository</span>
        </div>

        <div className="bg-[#111827]/80 backdrop-blur-sm border border-[#1F2937] rounded-2xl p-5 hover:border-emerald-500/40 transition-all group">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-xs font-medium uppercase tracking-wider">Published</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white tracking-tight">{loading ? '...' : metrics.published}</span>
          </div>
          <span className="text-[11px] text-gray-500 mt-1 block">Live across platforms</span>
        </div>

        <div className="bg-[#111827]/80 backdrop-blur-sm border border-[#1F2937] rounded-2xl p-5 hover:border-amber-500/40 transition-all group">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-xs font-medium uppercase tracking-wider">Scheduled</span>
            <Clock className="w-4 h-4 text-amber-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white tracking-tight">{loading ? '...' : metrics.scheduled}</span>
          </div>
          <span className="text-[11px] text-gray-500 mt-1 block">Upcoming queue items</span>
        </div>

        <div className="bg-[#111827]/80 backdrop-blur-sm border border-[#1F2937] rounded-2xl p-5 hover:border-rose-500/40 transition-all group">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-xs font-medium uppercase tracking-wider">Failed</span>
            <AlertCircle className="w-4 h-4 text-rose-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white tracking-tight">{loading ? '...' : metrics.failed}</span>
          </div>
          <span className="text-[11px] text-gray-500 mt-1 block">Action needed</span>
        </div>
      </div>

      {/* Main Grid: Recent Activity & Content Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Recent Activity */}
        <div className="lg:col-span-7 bg-[#111827]/80 border border-[#1F2937] rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="text-base font-semibold text-white">Recent Activity</h2>
                <p className="text-xs text-gray-400">Latest pipeline executions and status</p>
              </div>
              <Link href="/content" className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1">
                View all <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {loading ? (
              <div className="py-12 text-center text-xs text-gray-500 flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
                <span>Loading activity stream...</span>
              </div>
            ) : overview.recent_activity.length === 0 ? (
              <div className="py-12 text-center text-xs text-gray-500 space-y-2">
                <FolderOpen className="w-8 h-8 text-gray-600 mx-auto" />
                <p className="text-gray-400 font-medium">No recent activity yet</p>
                <p className="text-[11px]">Upload an asset or create a repurpose job to get started.</p>
              </div>
            ) : (
              <div className="divide-y divide-[#1F2937]">
                {overview.recent_activity.map((item) => (
                  <div key={item.id} className="py-3.5 flex items-center justify-between gap-4 first:pt-0 last:pb-0 px-2 hover:bg-[#161B26]/50 rounded-xl transition-colors">
                    <div className="flex items-center gap-3.5 min-w-0">
                      <div className="w-9 h-9 rounded-xl bg-[#161B26] border border-[#1F2937] flex items-center justify-center flex-shrink-0">
                        <Sparkles className="w-4 h-4 text-indigo-400" />
                      </div>
                      <div className="min-w-0">
                        <h4 className="text-xs font-semibold text-white truncate">{item.title}</h4>
                        <p className="text-[11px] text-gray-400 truncate">{item.created_at || 'Recently'}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 flex-shrink-0">
                      {statusBadge(item.status)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Content Distribution Donut Card */}
        <div className="lg:col-span-5 bg-[#111827]/80 border border-[#1F2937] rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-semibold text-white">Content Distribution</h2>
                <p className="text-xs text-gray-400">Total published volume across channels</p>
              </div>
            </div>

            <div className="flex items-center justify-center py-6">
              <div className="relative w-44 h-44 flex items-center justify-center">
                <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="38" fill="transparent" stroke="#1F2937" strokeWidth="12" />
                  {metrics.published > 0 && (
                    <circle
                      cx="50" cy="50" r="38"
                      fill="transparent"
                      stroke="#6366F1"
                      strokeWidth="12"
                      strokeDasharray="238.76"
                      strokeDashoffset="0"
                      strokeLinecap="round"
                    />
                  )}
                </svg>

                <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                  <span className="text-3xl font-extrabold text-white tracking-tight">{loading ? '...' : metrics.published}</span>
                  <span className="text-[11px] font-medium text-gray-400">Published</span>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-[#1F2937] text-center text-xs text-gray-500">
            {metrics.published === 0 ? "No published outputs yet" : `${metrics.published} live outputs distributed`}
          </div>
        </div>
      </div>

      {/* System Health Strip */}
      <div className="bg-[#111827]/60 border border-[#1F2937] rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full ${healthStatus === 'healthy' ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.8)]' : 'bg-amber-400'}`} />
          <span className="text-xs font-semibold text-white">
            {healthStatus === 'healthy' ? 'Self-Hosted Engine Operational' : 'Telemetry Degraded / Standalone'}
          </span>
        </div>
        <Link href="/system?tab=health" className="text-xs text-indigo-400 hover:text-indigo-300 font-medium">
          Health Telemetry &rarr;
        </Link>
      </div>
    </div>
  );
}
