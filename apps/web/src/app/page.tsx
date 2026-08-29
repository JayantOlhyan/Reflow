"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { 
  Sparkles, 
  ArrowUpRight, 
  Layers, 
  Clock, 
  AlertCircle, 
  CheckCircle2, 
  TrendingUp,
  Plus
} from 'lucide-react';
import { YoutubeIcon, InstagramIcon, TiktokIcon, LinkedinIcon, XIcon } from '@/components/ui/SocialIcons';

export default function OverviewPage() {
  const [metrics] = useState({
    total: 24,
    published: 18,
    scheduled: 6,
    failed: 2
  });

  const recentActivity = [
    { id: '1', title: 'Instagram Reel', subtitle: 'Building in Public, Day 20', status: 'published', platform: 'instagram', time: '2m ago' },
    { id: '2', title: 'YouTube Short', subtitle: 'AI Automation System', status: 'processing', platform: 'youtube', time: '5m ago' },
    { id: '3', title: 'LinkedIn Post', subtitle: '10 Lessons from building', status: 'scheduled', platform: 'linkedin', time: '1h ago' },
    { id: '4', title: 'X Post', subtitle: 'Quick update on the build', status: 'published', platform: 'x', time: '2h ago' },
    { id: '5', title: 'TikTok Video', subtitle: 'Behind the scenes', status: 'failed', platform: 'tiktok', time: '3h ago' }
  ];

  const distribution = [
    { platform: 'YouTube', count: 32, percentage: 38, color: '#EF4444' },
    { platform: 'Instagram', count: 21, percentage: 25, color: '#EC4899' },
    { platform: 'TikTok', count: 15, percentage: 18, color: '#06B6D4' },
    { platform: 'LinkedIn', count: 10, percentage: 12, color: '#3B82F6' },
    { platform: 'X', count: 6, percentage: 7, color: '#9CA3AF' },
  ];

  const statusBadge = (status: string) => {
    switch (status) {
      case 'published':
        return <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Published</span>;
      case 'processing':
        return <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 animate-pulse">Processing</span>;
      case 'scheduled':
        return <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20">Scheduled</span>;
      case 'failed':
        return <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-rose-500/10 text-rose-400 border border-rose-500/20">Failed</span>;
      default:
        return null;
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

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#111827]/80 backdrop-blur-sm border border-[#1F2937] rounded-2xl p-5 hover:border-indigo-500/40 transition-all group">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-xs font-medium uppercase tracking-wider">Total Content</span>
            <Layers className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white tracking-tight">{metrics.total}</span>
            <span className="text-xs text-emerald-400 font-medium flex items-center">
              +12% <TrendingUp className="w-3 h-3 ml-0.5" />
            </span>
          </div>
          <span className="text-[11px] text-gray-500 mt-1 block">Assets in repository</span>
        </div>

        <div className="bg-[#111827]/80 backdrop-blur-sm border border-[#1F2937] rounded-2xl p-5 hover:border-emerald-500/40 transition-all group">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-xs font-medium uppercase tracking-wider">Published</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white tracking-tight">{metrics.published}</span>
            <span className="text-xs text-emerald-400 font-medium">84 total posts</span>
          </div>
          <span className="text-[11px] text-gray-500 mt-1 block">Live across platforms</span>
        </div>

        <div className="bg-[#111827]/80 backdrop-blur-sm border border-[#1F2937] rounded-2xl p-5 hover:border-amber-500/40 transition-all group">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-xs font-medium uppercase tracking-wider">Scheduled</span>
            <Clock className="w-4 h-4 text-amber-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white tracking-tight">{metrics.scheduled}</span>
            <span className="text-xs text-amber-400 font-medium">Next: 7:30 PM</span>
          </div>
          <span className="text-[11px] text-gray-500 mt-1 block">Upcoming queue items</span>
        </div>

        <div className="bg-[#111827]/80 backdrop-blur-sm border border-[#1F2937] rounded-2xl p-5 hover:border-rose-500/40 transition-all group">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-xs font-medium uppercase tracking-wider">Failed</span>
            <AlertCircle className="w-4 h-4 text-rose-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white tracking-tight">{metrics.failed}</span>
            <span className="text-xs text-rose-400 font-medium">Action needed</span>
          </div>
          <span className="text-[11px] text-gray-500 mt-1 block">Auto-retry pending</span>
        </div>
      </div>

      {/* Main Grid: Recent Activity & Content Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Recent Activity */}
        <div className="lg:col-span-7 bg-[#111827]/80 border border-[#1F2937] rounded-2xl p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-base font-semibold text-white">Recent Activity</h2>
              <p className="text-xs text-gray-400">Latest pipeline executions and status</p>
            </div>
            <Link href="/content" className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1">
              View all <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="divide-y divide-[#1F2937]">
            {recentActivity.map((item) => (
              <div key={item.id} className="py-3.5 flex items-center justify-between gap-4 first:pt-0 last:pb-0 group hover:bg-[#161B26]/50 px-2 rounded-xl transition-colors">
                <div className="flex items-center gap-3.5 min-w-0">
                  <div className="w-9 h-9 rounded-xl bg-[#161B26] border border-[#1F2937] flex items-center justify-center flex-shrink-0">
                    {item.platform === 'youtube' && <YoutubeIcon className="w-4 h-4 text-red-400" />}
                    {item.platform === 'instagram' && <InstagramIcon className="w-4 h-4 text-pink-400" />}
                    {item.platform === 'linkedin' && <LinkedinIcon className="w-4 h-4 text-blue-400" />}
                    {item.platform === 'x' && <XIcon className="w-3.5 h-3.5 text-gray-300" />}
                    {item.platform === 'tiktok' && <TiktokIcon className="w-3.5 h-3.5 text-cyan-400" />}
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-xs font-semibold text-white truncate">{item.title}</h4>
                    <p className="text-[11px] text-gray-400 truncate">{item.subtitle}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 flex-shrink-0">
                  {statusBadge(item.status)}
                  <span className="text-[11px] text-gray-500 w-16 text-right">{item.time}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Content Distribution Donut Card */}
        <div className="lg:col-span-5 bg-[#111827]/80 border border-[#1F2937] rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-semibold text-white">Content Distribution</h2>
                <p className="text-xs text-gray-400">Last 7 days volume across channels</p>
              </div>
              <span className="text-xs font-medium text-gray-400 bg-[#161B26] px-2.5 py-1 rounded-lg border border-[#1F2937]">Last 7 days</span>
            </div>

            {/* Donut Graphic Visualizer */}
            <div className="flex items-center justify-center py-6">
              <div className="relative w-44 h-44 flex items-center justify-center">
                <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="38" fill="transparent" stroke="#1F2937" strokeWidth="12" />
                  <circle
                    cx="50" cy="50" r="38"
                    fill="transparent"
                    stroke="#EF4444"
                    strokeWidth="12"
                    strokeDasharray="238.76"
                    strokeDashoffset="0"
                    strokeLinecap="round"
                  />
                  <circle
                    cx="50" cy="50" r="38"
                    fill="transparent"
                    stroke="#8B5CF6"
                    strokeWidth="12"
                    strokeDasharray="60 178"
                    strokeDashoffset="-90"
                  />
                  <circle
                    cx="50" cy="50" r="38"
                    fill="transparent"
                    stroke="#06B6D4"
                    strokeWidth="12"
                    strokeDasharray="42 196"
                    strokeDashoffset="-150"
                  />
                  <circle
                    cx="50" cy="50" r="38"
                    fill="transparent"
                    stroke="#3B82F6"
                    strokeWidth="12"
                    strokeDasharray="28 210"
                    strokeDashoffset="-192"
                  />
                </svg>

                <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                  <span className="text-3xl font-extrabold text-white tracking-tight">84</span>
                  <span className="text-[11px] font-medium text-gray-400">Total Outputs</span>
                </div>
              </div>
            </div>
          </div>

          {/* Breakdown Legend */}
          <div className="space-y-2 pt-3 border-t border-[#1F2937]">
            {distribution.map((item) => (
              <div key={item.platform} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                  <span className="text-gray-300 font-medium">{item.platform}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-white font-semibold">{item.count}</span>
                  <span className="text-gray-500 text-[11px]">({item.percentage}%)</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* System Health Strip */}
      <div className="bg-[#111827]/60 border border-[#1F2937] rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.8)]" />
          <span className="text-xs font-semibold text-white">Self-Hosted Engine Operational</span>
        </div>
        <div className="flex items-center gap-6 text-xs text-gray-400">
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>Database: SQLite (Active)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>FFmpeg: Ready</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>AI: Gemini & OpenAI</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>Connected: 5/8 Platforms</span>
          </div>
        </div>
        <Link href="/system?tab=health" className="text-xs text-indigo-400 hover:text-indigo-300 font-medium">
          Health Details &rarr;
        </Link>
      </div>
    </div>
  );
}
