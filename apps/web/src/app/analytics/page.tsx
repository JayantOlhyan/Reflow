"use client";

import React, { useState, useEffect, useTransition } from 'react';
import { 
  Eye, ThumbsUp, MessageSquare, Share2, TrendingUp, TrendingDown,
  Download, RefreshCw, Filter, Calendar, BarChart2, Layers, AlertCircle,
  ExternalLink, Clock, ShieldCheck, CheckCircle2, XCircle, ArrowUpRight,
  ChevronRight, Sparkles, HelpCircle, X
} from 'lucide-react';
import { 
  YoutubeIcon, InstagramIcon, LinkedinIcon, XIcon, FacebookIcon, 
  TikTokIcon, PinterestIcon, ThreadsIcon 
} from '@/components/ui/SocialIcons';
import { api } from '@/lib/api';
import { 
  AnalyticsOverview, AnalyticsTimeseriesItem, PlatformAnalyticsItem, 
  ContentAnalyticsItem, PublicationAnalytics, PostMetricSnapshot 
} from '@/types';

function getPlatformIcon(platform: string) {
  const p = platform?.toLowerCase() || '';
  switch (p) {
    case 'youtube': return <YoutubeIcon className="w-4 h-4 text-red-500" />;
    case 'instagram': return <InstagramIcon className="w-4 h-4 text-pink-500" />;
    case 'linkedin': return <LinkedinIcon className="w-4 h-4 text-blue-500" />;
    case 'x': return <XIcon className="w-4 h-4 text-gray-300" />;
    case 'facebook': return <FacebookIcon className="w-4 h-4 text-blue-600" />;
    case 'tiktok': return <TikTokIcon className="w-4 h-4 text-cyan-400" />;
    case 'pinterest': return <PinterestIcon className="w-4 h-4 text-red-600" />;
    case 'threads': return <ThreadsIcon className="w-4 h-4 text-purple-400" />;
    default: return <BarChart2 className="w-4 h-4 text-gray-400" />;
  }
}

function formatNumber(num: number | null | undefined): string {
  if (num === null || num === undefined) return '—';
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toLocaleString();
}

function formatPercentage(num: number | null | undefined): string {
  if (num === null || num === undefined) return '—';
  return `${num.toFixed(1)}%`;
}

export default function AnalyticsPage() {
  const [rangePreset, setRangePreset] = useState<'7d' | '14d' | '30d' | '90d'>('30d');
  const [selectedPlatform, setSelectedPlatform] = useState<string>('all');
  const [selectedContentType, setSelectedContentType] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('views');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [timeseries, setTimeseries] = useState<AnalyticsTimeseriesItem[]>([]);
  const [platforms, setPlatforms] = useState<PlatformAnalyticsItem[]>([]);
  const [contents, setContents] = useState<ContentAnalyticsItem[]>([]);

  // Publication detail drawer state
  const [selectedPubId, setSelectedPubId] = useState<string | null>(null);
  const [pubAnalytics, setPubAnalytics] = useState<PublicationAnalytics | null>(null);
  const [pubLoading, setPubLoading] = useState(false);
  const [refreshingPub, setRefreshingPub] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);

  // Backfill modal state
  const [showBackfillModal, setShowBackfillModal] = useState(false);
  const [backfilling, setBackfilling] = useState(false);
  const [backfillCount, setBackfillCount] = useState<number | null>(null);

  const getDatesForPreset = (preset: string) => {
    const end = new Date();
    const start = new Date();
    if (preset === '7d') start.setDate(end.getDate() - 7);
    else if (preset === '14d') start.setDate(end.getDate() - 14);
    else if (preset === '30d') start.setDate(end.getDate() - 30);
    else if (preset === '90d') start.setDate(end.getDate() - 90);
    return {
      start: start.toISOString(),
      end: end.toISOString()
    };
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const { start, end } = getDatesForPreset(rangePreset);
      const platFilter = selectedPlatform !== 'all' ? selectedPlatform : undefined;
      const typeFilter = selectedContentType !== 'all' ? selectedContentType : undefined;

      const [ovData, tsData, plData, ctData] = await Promise.all([
        api.getAnalyticsOverview({ start, end, platform: platFilter, content_type: typeFilter }),
        api.getAnalyticsTimeseries({ start, end, platform: platFilter }),
        api.getPlatformAnalytics({ start, end }),
        api.getContentAnalytics({ start, end, content_type: typeFilter, sort_by: sortBy })
      ]);

      setOverview(ovData);
      setTimeseries(tsData.items || []);
      setPlatforms(plData || []);
      setContents(ctData || []);
    } catch (err: any) {
      console.error('Failed to load analytics:', err);
      setError(err.message || 'Failed to load analytics data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [rangePreset, selectedPlatform, selectedContentType, sortBy]);

  const loadPublicationDetail = async (pubId: string) => {
    setSelectedPubId(pubId);
    setPubLoading(true);
    setRefreshMessage(null);
    try {
      const res = await api.getPublicationAnalytics(pubId);
      setPubAnalytics(res);
    } catch (e: any) {
      console.error('Failed to load publication analytics:', e);
    } finally {
      setPubLoading(false);
    }
  };

  const handleManualRefresh = async () => {
    if (!selectedPubId) return;
    setRefreshingPub(true);
    setRefreshMessage(null);
    try {
      const res = await api.refreshPublicationAnalytics(selectedPubId);
      setRefreshMessage(res.message || 'Metrics sync queued. Refreshing data in a moment...');
      setTimeout(() => {
        loadPublicationDetail(selectedPubId);
      }, 3000);
    } catch (e: any) {
      setRefreshMessage(e.message || 'Refresh failed.');
    } finally {
      setRefreshingPub(false);
    }
  };

  const handleTriggerBackfill = async () => {
    setBackfilling(true);
    try {
      const { start, end } = getDatesForPreset(rangePreset);
      const res = await api.backfillAnalytics({
        start_date: start,
        end_date: end,
        platform: selectedPlatform !== 'all' ? selectedPlatform : undefined,
        limit: 50
      });
      setBackfillCount(res.queued_count);
      setTimeout(() => {
        setShowBackfillModal(false);
        setBackfillCount(null);
        loadData();
      }, 2000);
    } catch (e: any) {
      alert(e.message || 'Backfill failed');
    } finally {
      setBackfilling(false);
    }
  };

  const exportUrl = api.getAnalyticsExportUrl({
    ...getDatesForPreset(rangePreset),
    platform: selectedPlatform !== 'all' ? selectedPlatform : undefined
  });

  return (
    <div className="space-y-6 animate-fadeIn pb-16">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-[#1F2937] pb-5">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <BarChart2 className="w-6 h-6 text-indigo-400" />
            Analytics & Performance Intelligence
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            Real-time multi-platform metric ingestion, historical snapshot tracking, and performance attribution.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Range Presets */}
          <div className="flex items-center bg-[#111827] border border-[#1F2937] rounded-xl p-1 text-xs">
            {(['7d', '14d', '30d', '90d'] as const).map((p) => (
              <button
                key={p}
                onClick={() => setRangePreset(p)}
                className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                  rangePreset === p
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {p.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Platform Filter */}
          <select
            value={selectedPlatform}
            onChange={(e) => setSelectedPlatform(e.target.value)}
            className="bg-[#111827] border border-[#1F2937] rounded-xl px-3 py-2 text-xs font-semibold text-gray-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Platforms</option>
            <option value="youtube">YouTube</option>
            <option value="instagram">Instagram</option>
            <option value="linkedin">LinkedIn</option>
            <option value="x">X (Twitter)</option>
            <option value="facebook">Facebook</option>
          </select>

          {/* Content Type Filter */}
          <select
            value={selectedContentType}
            onChange={(e) => setSelectedContentType(e.target.value)}
            className="bg-[#111827] border border-[#1F2937] rounded-xl px-3 py-2 text-xs font-semibold text-gray-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Content Types</option>
            <option value="VIDEO">Video</option>
            <option value="IMAGE">Image</option>
            <option value="CAROUSEL">Carousel</option>
            <option value="TEXT">Text</option>
          </select>

          {/* Action Buttons */}
          <button
            onClick={() => setShowBackfillModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 bg-[#1F2937] hover:bg-[#283548] text-gray-200 hover:text-white rounded-xl text-xs font-semibold transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Sync / Backfill
          </button>

          <a
            href={exportUrl}
            download
            className="flex items-center gap-1.5 px-3 py-2 bg-indigo-600/20 border border-indigo-500/30 hover:bg-indigo-600/30 text-indigo-300 rounded-xl text-xs font-semibold transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            Export CSV
          </a>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-4 flex items-center gap-3 text-red-400 text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Top Level Metric KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Publications */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400">Total Published Posts</span>
            <Layers className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">
              {overview ? overview.total_publications : '0'}
            </span>
            {overview?.period_comparison?.total_publications_change_pct !== null && overview?.period_comparison?.total_publications_change_pct !== undefined && (
              <span className={`text-xs font-semibold flex items-center ${
                overview.period_comparison.total_publications_change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                {overview.period_comparison.total_publications_change_pct >= 0 ? '+' : ''}
                {overview.period_comparison.total_publications_change_pct}%
              </span>
            )}
          </div>
          <p className="text-[11px] text-gray-500">Across {platforms.filter(p => p.publication_count > 0).length} active social channels</p>
        </div>

        {/* Total Views / Impressions */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400">Total Views / Plays</span>
            <Eye className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight font-mono">
              {formatNumber(overview?.total_views)}
            </span>
            {overview?.period_comparison?.total_views_change_pct !== null && overview?.period_comparison?.total_views_change_pct !== undefined && (
              <span className={`text-xs font-semibold flex items-center ${
                overview.period_comparison.total_views_change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                {overview.period_comparison.total_views_change_pct >= 0 ? '+' : ''}
                {overview.period_comparison.total_views_change_pct}%
              </span>
            )}
          </div>
          <p className="text-[11px] text-gray-500">
            Impressions: {formatNumber(overview?.total_impressions)}
          </p>
        </div>

        {/* Total Engagements */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400">Total Engagements</span>
            <ThumbsUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight font-mono">
              {formatNumber(overview?.total_engagements)}
            </span>
            {overview?.period_comparison?.total_engagements_change_pct !== null && overview?.period_comparison?.total_engagements_change_pct !== undefined && (
              <span className={`text-xs font-semibold flex items-center ${
                overview.period_comparison.total_engagements_change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                {overview.period_comparison.total_engagements_change_pct >= 0 ? '+' : ''}
                {overview.period_comparison.total_engagements_change_pct}%
              </span>
            )}
          </div>
          <p className="text-[11px] text-gray-500">Likes, comments, shares, saves</p>
        </div>

        {/* Avg Engagement Rate */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400">Avg Engagement Rate</span>
            <TrendingUp className="w-4 h-4 text-purple-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight font-mono">
              {formatPercentage(overview?.average_engagement_rate)}
            </span>
          </div>
          <p className="text-[11px] text-gray-500">
            Avg views/post: {formatNumber(overview?.average_views_per_publication)}
          </p>
        </div>
      </div>

      {/* Timeseries Daily Trend Chart */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white">Daily Performance & Volume Trend</h2>
            <p className="text-xs text-gray-400 mt-0.5">Aggregated daily impressions and engagement velocity</p>
          </div>
          <div className="flex items-center gap-4 text-xs font-semibold">
            <div className="flex items-center gap-1.5 text-cyan-400">
              <span className="w-2.5 h-2.5 rounded-sm bg-cyan-500 inline-block"></span>
              <span>Views</span>
            </div>
            <div className="flex items-center gap-1.5 text-emerald-400">
              <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500 inline-block"></span>
              <span>Engagements</span>
            </div>
          </div>
        </div>

        {timeseries.length === 0 ? (
          <div className="h-44 flex items-center justify-center text-xs text-gray-500 border border-dashed border-[#1F2937] rounded-xl">
            No publication data recorded in this period.
          </div>
        ) : (
          <div className="h-48 flex items-end gap-1 pt-6 pb-2 px-1 overflow-x-auto">
            {timeseries.map((item, idx) => {
              const maxViews = Math.max(...timeseries.map(t => t.views || 0), 10);
              const maxEng = Math.max(...timeseries.map(t => t.engagements || 0), 5);
              const viewHeight = item.views ? Math.max(8, (item.views / maxViews) * 100) : 0;
              const engHeight = item.engagements ? Math.max(8, (item.engagements / maxEng) * 70) : 0;

              return (
                <div key={item.date} className="flex-1 min-w-[20px] flex flex-col items-center gap-1 group relative">
                  {/* Hover Tooltip */}
                  <div className="absolute bottom-full mb-2 hidden group-hover:flex flex-col bg-[#1E293B] border border-[#334155] p-2 rounded-lg text-[10px] text-gray-200 z-20 shadow-xl whitespace-nowrap">
                    <span className="font-bold text-white">{item.date}</span>
                    <span>Views: {formatNumber(item.views)}</span>
                    <span>Engagements: {formatNumber(item.engagements)}</span>
                    <span>Posts: {item.publications_count}</span>
                  </div>

                  <div className="w-full flex items-end justify-center gap-0.5 h-32">
                    {item.views !== null && item.views !== undefined ? (
                      <div
                        style={{ height: `${viewHeight}%` }}
                        className="w-1/2 bg-cyan-500/80 hover:bg-cyan-400 rounded-t transition-all"
                      ></div>
                    ) : (
                      <div className="w-1/2 h-1 bg-gray-800 rounded-t"></div>
                    )}
                    {item.engagements !== null && item.engagements !== undefined ? (
                      <div
                        style={{ height: `${engHeight}%` }}
                        className="w-1/2 bg-emerald-500/80 hover:bg-emerald-400 rounded-t transition-all"
                      ></div>
                    ) : (
                      <div className="w-1/2 h-1 bg-gray-800 rounded-t"></div>
                    )}
                  </div>
                  {idx % Math.ceil(timeseries.length / 10) === 0 && (
                    <span className="text-[9px] text-gray-500 mt-1">{item.date.slice(5)}</span>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Two Column Layout: Platform Matrix & Top Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Platform Breakdown */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white">Platform Performance Matrix</h2>
            <span className="text-xs text-gray-500 font-semibold">{platforms.length} Platforms</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#1F2937] text-gray-400 font-semibold">
                  <th className="pb-3">Platform</th>
                  <th className="pb-3">Posts</th>
                  <th className="pb-3">Views</th>
                  <th className="pb-3">Engagements</th>
                  <th className="pb-3">Eng. Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1F2937]">
                {platforms.map((p) => (
                  <tr key={p.platform} className="hover:bg-[#161B26] transition-colors">
                    <td className="py-3 flex items-center gap-2.5 font-bold text-white capitalize">
                      {getPlatformIcon(p.platform)}
                      <span>{p.platform}</span>
                      {!p.supports_analytics && (
                        <span className="text-[9px] px-1.5 py-0.5 bg-gray-800 text-gray-400 rounded font-normal">
                          No API
                        </span>
                      )}
                    </td>
                    <td className="py-3 text-gray-300 font-mono">{p.publication_count}</td>
                    <td className="py-3 text-gray-300 font-mono">{formatNumber(p.total_views)}</td>
                    <td className="py-3 text-gray-300 font-mono">{formatNumber(p.total_engagements)}</td>
                    <td className="py-3 text-emerald-400 font-bold font-mono">
                      {formatPercentage(p.engagement_rate)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Content Attribution Leaderboard */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-white">Top Performing Content</h2>
              <p className="text-xs text-gray-400">Attributed across variants and published posts</p>
            </div>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-[#1F2937] border border-[#374151] rounded-lg px-2.5 py-1 text-xs font-semibold text-gray-300 focus:outline-none"
            >
              <option value="views">Sort by Views</option>
              <option value="engagements">Sort by Engagements</option>
              <option value="engagement_rate">Sort by Eng Rate</option>
            </select>
          </div>

          <div className="space-y-3">
            {contents.length === 0 ? (
              <div className="p-8 text-center text-xs text-gray-500 border border-dashed border-[#1F2937] rounded-xl">
                No published content found for selected filter criteria.
              </div>
            ) : (
              contents.slice(0, 5).map((cnt) => (
                <div
                  key={cnt.content_id}
                  className="p-3.5 bg-[#161F30] hover:bg-[#1E293B] border border-[#1F2937] rounded-xl flex items-center justify-between gap-3 transition-colors"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-lg bg-gray-800 flex items-center justify-center text-gray-400 text-xs font-bold flex-shrink-0">
                      {cnt.content_type.slice(0, 3)}
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-white truncate">{cnt.title}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[10px] px-1.5 py-0.5 bg-indigo-500/20 text-indigo-300 rounded font-semibold">
                          {cnt.content_type}
                        </span>
                        <div className="flex items-center gap-1">
                          {cnt.platforms.map((plat) => (
                            <span key={plat} title={plat}>{getPlatformIcon(plat)}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 text-right flex-shrink-0">
                    <div>
                      <span className="text-xs font-bold text-white font-mono block">
                        {formatNumber(cnt.total_views)}
                      </span>
                      <span className="text-[10px] text-gray-500">Views</span>
                    </div>
                    <div>
                      <span className="text-xs font-bold text-emerald-400 font-mono block">
                        {formatPercentage(cnt.engagement_rate)}
                      </span>
                      <span className="text-[10px] text-gray-500">Eng Rate</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Publication Drill-down Drawer */}
      {selectedPubId && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex justify-end animate-fadeIn">
          <div className="w-full max-w-lg bg-[#0F172A] border-l border-[#1E293B] h-full p-6 overflow-y-auto space-y-6 flex flex-col justify-between">
            <div className="space-y-6">
              {/* Drawer Header */}
              <div className="flex items-center justify-between border-b border-[#1E293B] pb-4">
                <div className="flex items-center gap-2.5">
                  {pubAnalytics && getPlatformIcon(pubAnalytics.publication.platform)}
                  <div>
                    <h3 className="text-base font-bold text-white">Publication Analytics</h3>
                    <p className="text-xs text-gray-400 capitalize">
                      {pubAnalytics?.publication.platform} • {pubAnalytics?.publication.status}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedPubId(null)}
                  className="p-1.5 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {pubLoading ? (
                <div className="py-20 text-center text-xs text-gray-400">Loading metrics...</div>
              ) : pubAnalytics ? (
                <div className="space-y-6">
                  {/* Status & Freshness Badge */}
                  <div className="flex items-center justify-between p-3.5 bg-[#1E293B] rounded-xl">
                    <div className="flex items-center gap-2">
                      {pubAnalytics.is_stale ? (
                        <AlertCircle className="w-4 h-4 text-amber-400" />
                      ) : (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      )}
                      <div>
                        <span className="text-xs font-bold text-white block">
                          {pubAnalytics.is_stale ? 'Data Stale (>24h)' : 'Fresh Snapshot'}
                        </span>
                        <span className="text-[10px] text-gray-400">
                          Last synced: {pubAnalytics.latest_snapshot ? new Date(pubAnalytics.latest_snapshot.captured_at).toLocaleString() : 'Never'}
                        </span>
                      </div>
                    </div>

                    <button
                      onClick={handleManualRefresh}
                      disabled={refreshingPub}
                      className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-colors"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${refreshingPub ? 'animate-spin' : ''}`} />
                      Refresh
                    </button>
                  </div>

                  {refreshMessage && (
                    <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs rounded-xl">
                      {refreshMessage}
                    </div>
                  )}

                  {/* Growth Velocity */}
                  {(pubAnalytics.views_per_hour !== null || pubAnalytics.engagements_per_hour !== null) && (
                    <div className="grid grid-cols-2 gap-3">
                      <div className="p-3 bg-[#161F30] border border-[#1E293B] rounded-xl">
                        <span className="text-[10px] text-gray-400 font-semibold block">Velocity (Views / Hr)</span>
                        <span className="text-lg font-bold text-cyan-400 font-mono">
                          +{pubAnalytics.views_per_hour || 0}
                        </span>
                      </div>
                      <div className="p-3 bg-[#161F30] border border-[#1E293B] rounded-xl">
                        <span className="text-[10px] text-gray-400 font-semibold block">Velocity (Eng / Hr)</span>
                        <span className="text-lg font-bold text-emerald-400 font-mono">
                          +{pubAnalytics.engagements_per_hour || 0}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Latest Metrics Breakdown */}
                  {pubAnalytics.latest_snapshot ? (
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">Current Metrics</h4>
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div className="p-3 bg-[#161F30] rounded-xl">
                          <span className="text-gray-400 block text-[10px]">Views</span>
                          <span className="text-base font-bold text-white font-mono">
                            {formatNumber(pubAnalytics.latest_snapshot.views)}
                          </span>
                        </div>
                        <div className="p-3 bg-[#161F30] rounded-xl">
                          <span className="text-gray-400 block text-[10px]">Impressions</span>
                          <span className="text-base font-bold text-white font-mono">
                            {formatNumber(pubAnalytics.latest_snapshot.impressions)}
                          </span>
                        </div>
                        <div className="p-3 bg-[#161F30] rounded-xl">
                          <span className="text-gray-400 block text-[10px]">Likes</span>
                          <span className="text-base font-bold text-white font-mono">
                            {formatNumber(pubAnalytics.latest_snapshot.likes)}
                          </span>
                        </div>
                        <div className="p-3 bg-[#161F30] rounded-xl">
                          <span className="text-gray-400 block text-[10px]">Comments</span>
                          <span className="text-base font-bold text-white font-mono">
                            {formatNumber(pubAnalytics.latest_snapshot.comments)}
                          </span>
                        </div>
                        <div className="p-3 bg-[#161F30] rounded-xl">
                          <span className="text-gray-400 block text-[10px]">Shares</span>
                          <span className="text-base font-bold text-white font-mono">
                            {formatNumber(pubAnalytics.latest_snapshot.shares)}
                          </span>
                        </div>
                        <div className="p-3 bg-[#161F30] rounded-xl">
                          <span className="text-gray-400 block text-[10px]">Engagement Rate</span>
                          <span className="text-base font-bold text-emerald-400 font-mono">
                            {formatPercentage(pubAnalytics.latest_snapshot.engagement_rate)}
                          </span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="p-6 text-center text-xs text-gray-500 border border-dashed border-[#1E293B] rounded-xl">
                      No metric snapshot captured yet. Click refresh to trigger sync.
                    </div>
                  )}

                  {/* Historical Snapshot Timeline */}
                  {pubAnalytics.snapshots.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">
                        Snapshot History ({pubAnalytics.snapshots.length})
                      </h4>
                      <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                        {pubAnalytics.snapshots.map((snap) => (
                          <div
                            key={snap.id}
                            className="p-2.5 bg-[#161F30] rounded-lg flex items-center justify-between text-xs font-mono"
                          >
                            <span className="text-gray-400 text-[10px]">
                              {new Date(snap.captured_at).toLocaleTimeString()}
                            </span>
                            <div className="flex items-center gap-3">
                              <span className="text-cyan-400">Views: {formatNumber(snap.views)}</span>
                              <span className="text-emerald-400">Likes: {formatNumber(snap.likes)}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>

            <div className="border-t border-[#1E293B] pt-4">
              <button
                onClick={() => setSelectedPubId(null)}
                className="w-full py-2.5 bg-[#1E293B] hover:bg-[#283548] text-white text-xs font-bold rounded-xl transition-colors"
              >
                Close Drawer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Backfill Modal */}
      {showBackfillModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-white">Trigger Metric Backfill & Sweep</h3>
            <p className="text-xs text-gray-400">
              This will enqueue asynchronous background worker jobs to query the official platform APIs for published posts within the selected time window.
            </p>

            <div className="p-3 bg-[#1F2937] rounded-xl text-xs space-y-1">
              <div className="flex justify-between">
                <span className="text-gray-400">Range:</span>
                <span className="text-white font-semibold">{rangePreset.toUpperCase()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Platform:</span>
                <span className="text-white font-semibold capitalize">{selectedPlatform}</span>
              </div>
            </div>

            {backfillCount !== null && (
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs rounded-xl flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                <span>Successfully queued {backfillCount} metrics sync job(s).</span>
              </div>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowBackfillModal(false)}
                className="px-4 py-2 bg-gray-800 text-gray-300 text-xs font-semibold rounded-xl hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={handleTriggerBackfill}
                disabled={backfilling}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${backfilling ? 'animate-spin' : ''}`} />
                {backfilling ? 'Queuing Jobs...' : 'Confirm Sync'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
