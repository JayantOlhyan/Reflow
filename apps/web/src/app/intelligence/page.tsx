"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  Sparkles, 
  Lightbulb, 
  TrendingUp, 
  TrendingDown, 
  Compass, 
  Clock, 
  Film, 
  Layers, 
  Calendar, 
  CheckCircle2, 
  AlertCircle, 
  RefreshCw, 
  HelpCircle,
  FlaskConical,
  Target,
  ArrowRight,
  ShieldCheck,
  Zap,
  BarChart3
} from 'lucide-react';
import { 
  IntelligenceOverview, 
  ContentRecommendation, 
  PerformanceInsight, 
  TopicPerformanceItem, 
  HookPerformanceItem, 
  DurationPerformanceItem, 
  PostingWindowItem, 
  ContentGapItem, 
  Experiment 
} from '@/types';
import { api } from '@/lib/api';

export default function IntelligencePage() {
  const [overview, setOverview] = useState<IntelligenceOverview | null>(null);
  const [recommendations, setRecommendations] = useState<ContentRecommendation[]>([]);
  const [insights, setInsights] = useState<PerformanceInsight[]>([]);
  const [topics, setTopics] = useState<TopicPerformanceItem[]>([]);
  const [hooks, setHooks] = useState<HookPerformanceItem[]>([]);
  const [durations, setDurations] = useState<DurationPerformanceItem[]>([]);
  const [windows, setWindows] = useState<PostingWindowItem[]>([]);
  const [gaps, setGaps] = useState<ContentGapItem[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);

  const [activeTab, setActiveTab] = useState<'recs' | 'hooks' | 'topics' | 'durations' | 'windows' | 'gaps' | 'experiments'>('recs');
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [ovRes, recRes, insRes, topRes, hkRes, durRes, winRes, gapRes, expRes] = await Promise.all([
        api.getIntelligenceOverview().catch(() => null),
        api.getContentRecommendations().catch(() => []),
        api.getIntelligenceInsights().catch(() => []),
        api.getTopicPerformance().catch(() => []),
        api.getHookPerformance().catch(() => []),
        api.getDurationPerformance().catch(() => []),
        api.getPostingWindows().catch(() => []),
        api.getContentGaps().catch(() => []),
        api.getExperiments().catch(() => [])
      ]);

      setOverview(ovRes);
      setRecommendations(recRes || []);
      setInsights(insRes || []);
      setTopics(topRes || []);
      setHooks(hkRes || []);
      setDurations(durRes || []);
      setWindows(winRes || []);
      setGaps(gapRes || []);
      setExperiments(expRes || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      setRefreshMessage(null);
      await api.refreshIntelligence();
      setRefreshMessage("Intelligence refresh job dispatched to worker queue.");
      setTimeout(() => {
        loadData();
        setRefreshMessage(null);
      }, 2500);
    } catch (e: any) {
      setRefreshMessage(e?.message || "Failed to trigger refresh.");
    } finally {
      setRefreshing(false);
    }
  };

  const getConfidenceBadge = (confidence: string) => {
    switch (confidence) {
      case 'HIGH':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">HIGH CONFIDENCE</span>;
      case 'MEDIUM':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">MEDIUM CONFIDENCE</span>;
      case 'LOW':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">LOW CONFIDENCE</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">INSUFFICIENT DATA</span>;
    }
  };

  const getActionUrl = (rec: ContentRecommendation) => {
    if (rec.action_type === 'CREATE_CLIP') {
      const cId = rec.action_payload?.content_id;
      return cId ? `/repurpose?contentId=${cId}` : '/repurpose';
    }
    if (rec.action_type === 'CREATE_CAROUSEL') {
      const top = rec.action_payload?.topic;
      return top ? `/carousel?topic=${encodeURIComponent(top)}` : '/carousel';
    }
    if (rec.action_type === 'SCHEDULE_POST') {
      return '/calendar';
    }
    return '/content';
  };

  const getActionLabel = (rec: ContentRecommendation) => {
    if (rec.action_type === 'CREATE_CLIP') return 'Open Repurpose Studio';
    if (rec.action_type === 'CREATE_CAROUSEL') return 'Open Carousel Studio';
    if (rec.action_type === 'SCHEDULE_POST') return 'Open Calendar Scheduler';
    return 'View Content Library';
  };

  if (loading && !overview) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <RefreshCw className="w-8 h-8 text-primary animate-spin" />
        <p className="text-sm text-slate-400">Synthesizing content patterns and recommendations...</p>
      </div>
    );
  }

  const isColdStart = !overview?.is_sufficient_data;

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-3 mb-1.5">
            <h1 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center gap-2.5">
              <Sparkles className="w-6 h-6 text-primary" />
              Content Intelligence & Recommendations
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20">
              Phase 11
            </span>
          </div>
          <p className="text-sm text-slate-400">
            Evidence-backed performance patterns, content gaps, and deterministic recommendations derived from your historical Reflow data.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {overview?.last_analyzed_at && (
            <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-900/60 border border-slate-800 px-3 py-1.5 rounded-lg">
              <Clock className="w-3.5 h-3.5 text-slate-500" />
              <span>Analyzed: {new Date(overview.last_analyzed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
              {overview.is_stale ? (
                <span className="px-1.5 py-0.2 rounded text-[10px] bg-amber-500/10 text-amber-400 font-medium">Stale</span>
              ) : (
                <span className="px-1.5 py-0.2 rounded text-[10px] bg-emerald-500/10 text-emerald-400 font-medium">Fresh</span>
              )}
            </div>
          )}

          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-3.5 py-1.5 bg-primary text-slate-950 font-semibold text-xs rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 cursor-pointer shadow-sm shadow-primary/20"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            <span>{refreshing ? 'Analyzing...' : 'Refresh Intelligence'}</span>
          </button>
        </div>
      </div>

      {refreshMessage && (
        <div className="p-3 bg-slate-900 border border-primary/30 rounded-xl text-xs text-primary flex items-center gap-2">
          <Zap className="w-4 h-4" />
          <span>{refreshMessage}</span>
        </div>
      )}

      {/* Cold Start Guidance Banner */}
      {isColdStart && (
        <div className="p-5 bg-gradient-to-r from-amber-950/20 via-slate-900 to-slate-900 border border-amber-500/30 rounded-2xl space-y-3">
          <div className="flex items-center gap-2 text-amber-400 font-semibold text-sm">
            <AlertCircle className="w-4 h-4" />
            <span>GENERAL GUIDANCE (Cold Start Active)</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Reflow requires at least <strong className="text-amber-300 font-semibold">{overview?.minimum_samples_required || 5} published posts</strong> with synced performance analytics before generating personalized statistical recommendations. Currently, <strong className="text-slate-100">{overview?.total_analyzed_posts || 0} posts</strong> have been analyzed.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1">
              <div className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                <Target className="w-3.5 h-3.5 text-primary" /> Hook Principle
              </div>
              <p className="text-[11px] text-slate-400">Open with a clear question or statistic in the first 3 seconds to maximize short-form retention.</p>
            </div>
            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1">
              <div className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                <Film className="w-3.5 h-3.5 text-primary" /> Clip Durations
              </div>
              <p className="text-[11px] text-slate-400">Aim for 20–45s for Instagram Reels and TikTok; 45–60s for YouTube Shorts.</p>
            </div>
            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1">
              <div className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-primary" /> Carousel Density
              </div>
              <p className="text-[11px] text-slate-400">Use 5–7 slides with 1 clear takeaway per slide using minimal typography.</p>
            </div>
          </div>
        </div>
      )}

      {/* Top KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl flex flex-col justify-between">
          <span className="text-xs font-medium text-slate-400">Analyzed Publications</span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-100">{overview?.total_analyzed_posts || 0}</span>
            <span className="text-xs text-slate-500">posts tracked</span>
          </div>
          <span className="text-[11px] text-slate-500 mt-2">Historical sample baseline</span>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl flex flex-col justify-between">
          <span className="text-xs font-medium text-slate-400">Account Baseline ER</span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-100">
              {overview?.account_baseline_engagement_rate != null ? `${overview.account_baseline_engagement_rate}%` : '—'}
            </span>
            <span className="text-xs text-slate-500">median ER</span>
          </div>
          <span className="text-[11px] text-slate-500 mt-2">Trimmed distribution median</span>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl flex flex-col justify-between">
          <span className="text-xs font-medium text-slate-400">Account Baseline Views</span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-100">
              {overview?.account_baseline_views != null ? Math.round(overview.account_baseline_views).toLocaleString() : '—'}
            </span>
            <span className="text-xs text-slate-500">median views</span>
          </div>
          <span className="text-[11px] text-slate-500 mt-2">Outlier-resistant median</span>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl flex flex-col justify-between">
          <span className="text-xs font-medium text-slate-400">Active Content Gaps</span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-primary">{gaps.length}</span>
            <span className="text-xs text-slate-500">opportunities</span>
          </div>
          <span className="text-[11px] text-slate-500 mt-2">High-performing gaps found</span>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800 overflow-x-auto pb-2">
        <button
          onClick={() => setActiveTab('recs')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap flex items-center gap-1.5 cursor-pointer ${
            activeTab === 'recs' ? 'bg-primary text-slate-950 font-semibold' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Lightbulb className="w-3.5 h-3.5" />
          <span>Recommendations ({recommendations.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('hooks')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap flex items-center gap-1.5 cursor-pointer ${
            activeTab === 'hooks' ? 'bg-primary text-slate-950 font-semibold' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Target className="w-3.5 h-3.5" />
          <span>Hook Analysis ({hooks.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('topics')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap flex items-center gap-1.5 cursor-pointer ${
            activeTab === 'topics' ? 'bg-primary text-slate-950 font-semibold' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Compass className="w-3.5 h-3.5" />
          <span>Topic Clusters ({topics.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('durations')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap flex items-center gap-1.5 cursor-pointer ${
            activeTab === 'durations' ? 'bg-primary text-slate-950 font-semibold' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Film className="w-3.5 h-3.5" />
          <span>Durations ({durations.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('windows')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap flex items-center gap-1.5 cursor-pointer ${
            activeTab === 'windows' ? 'bg-primary text-slate-950 font-semibold' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Calendar className="w-3.5 h-3.5" />
          <span>Posting Windows ({windows.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('gaps')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap flex items-center gap-1.5 cursor-pointer ${
            activeTab === 'gaps' ? 'bg-primary text-slate-950 font-semibold' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Content Gaps ({gaps.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('experiments')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap flex items-center gap-1.5 cursor-pointer ${
            activeTab === 'experiments' ? 'bg-primary text-slate-950 font-semibold' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <FlaskConical className="w-3.5 h-3.5" />
          <span>Experiments ({experiments.length})</span>
        </button>
      </div>

      {/* Tab Contents */}
      {activeTab === 'recs' && (
        <div className="space-y-4">
          {recommendations.length === 0 ? (
            <div className="text-center py-12 bg-slate-900/40 border border-slate-800/80 rounded-2xl">
              <CheckCircle2 className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-sm font-medium text-slate-300">No recommendations available yet</p>
              <p className="text-xs text-slate-500 mt-1">Publish more content and sync analytics to generate recommendations.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {recommendations.map((rec) => (
                <div key={rec.id} className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl flex flex-col justify-between hover:border-slate-700 transition-colors space-y-4">
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[11px] font-medium tracking-wide uppercase text-primary px-2 py-0.5 bg-primary/10 rounded border border-primary/20">
                        {rec.type.replace(/_/g, ' ')}
                      </span>
                      {getConfidenceBadge(rec.confidence)}
                    </div>
                    <h3 className="text-base font-semibold text-slate-100">{rec.title}</h3>
                    <p className="text-xs text-slate-300 leading-relaxed">{rec.recommendation_text}</p>
                    <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1.5 text-xs">
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Evidence & Context</span>
                      <p className="text-slate-300 text-[11px] leading-relaxed">{rec.why_text}</p>
                      <div className="flex items-center gap-4 text-[11px] text-slate-400 pt-1 border-t border-slate-900">
                        <span>Sample Size: <strong className="text-slate-200">{rec.sample_size}</strong></span>
                        {rec.evidence?.median_er && (
                          <span>Median ER: <strong className="text-emerald-400">{rec.evidence.median_er}%</strong></span>
                        )}
                        {rec.evidence?.baseline_er && (
                          <span>Baseline: <strong className="text-slate-300">{rec.evidence.baseline_er}%</strong></span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="pt-2">
                    <Link
                      href={getActionUrl(rec)}
                      className="inline-flex items-center justify-center gap-1.5 w-full py-2 px-3.5 bg-primary/10 text-primary hover:bg-primary hover:text-slate-950 font-semibold text-xs rounded-xl border border-primary/20 transition-colors"
                    >
                      <span>{getActionLabel(rec)}</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'hooks' && (
        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Target className="w-4 h-4 text-primary" />
              Hook Archetype Performance Breakdown
            </h3>
            <span className="text-xs text-slate-500">8 Standard Classifications</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 text-slate-400 font-medium">
                <tr>
                  <th className="py-2.5 px-3">Hook Archetype</th>
                  <th className="py-2.5 px-3">Sample Count</th>
                  <th className="py-2.5 px-3">Median Engagement Rate</th>
                  <th className="py-2.5 px-3">Vs Account Baseline</th>
                  <th className="py-2.5 px-3">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {hooks.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-slate-500">No hook performance data recorded yet.</td>
                  </tr>
                ) : (
                  hooks.map((hk, i) => (
                    <tr key={i} className="hover:bg-slate-800/30">
                      <td className="py-2.5 px-3 font-semibold text-slate-200">{hk.hook_type.replace(/_/g, ' ')}</td>
                      <td className="py-2.5 px-3">{hk.sample_size} posts</td>
                      <td className="py-2.5 px-3 font-medium text-slate-100">{hk.median_engagement_rate != null ? `${hk.median_engagement_rate}%` : '—'}</td>
                      <td className="py-2.5 px-3">
                        {hk.performance_vs_baseline_pct != null ? (
                          <span className={`font-semibold flex items-center gap-1 ${hk.performance_vs_baseline_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {hk.performance_vs_baseline_pct >= 0 ? '+' : ''}{hk.performance_vs_baseline_pct}%
                          </span>
                        ) : '—'}
                      </td>
                      <td className="py-2.5 px-3">{getConfidenceBadge(hk.confidence)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'topics' && (
        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Compass className="w-4 h-4 text-primary" />
              Normalized Topic Performance Clusters
            </h3>
            <span className="text-xs text-slate-500">Aggregated Clusters</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 text-slate-400 font-medium">
                <tr>
                  <th className="py-2.5 px-3">Topic Cluster</th>
                  <th className="py-2.5 px-3">Sample Count</th>
                  <th className="py-2.5 px-3">Median Engagement Rate</th>
                  <th className="py-2.5 px-3">Vs Account Baseline</th>
                  <th className="py-2.5 px-3">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {topics.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-slate-500">No topic performance data recorded yet.</td>
                  </tr>
                ) : (
                  topics.map((top, i) => (
                    <tr key={i} className="hover:bg-slate-800/30">
                      <td className="py-2.5 px-3 font-semibold text-slate-200 capitalize">{top.topic.replace(/-/g, ' ')}</td>
                      <td className="py-2.5 px-3">{top.sample_size} posts</td>
                      <td className="py-2.5 px-3 font-medium text-slate-100">{top.median_engagement_rate != null ? `${top.median_engagement_rate}%` : '—'}</td>
                      <td className="py-2.5 px-3">
                        {top.performance_vs_baseline_pct != null ? (
                          <span className={`font-semibold flex items-center gap-1 ${top.performance_vs_baseline_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {top.performance_vs_baseline_pct >= 0 ? '+' : ''}{top.performance_vs_baseline_pct}%
                          </span>
                        ) : '—'}
                      </td>
                      <td className="py-2.5 px-3">{getConfidenceBadge(top.confidence)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'durations' && (
        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Film className="w-4 h-4 text-primary" />
              Short-Form Video Duration Buckets
            </h3>
            <span className="text-xs text-slate-500">0s to 120s+</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 text-slate-400 font-medium">
                <tr>
                  <th className="py-2.5 px-3">Duration Range</th>
                  <th className="py-2.5 px-3">Sample Count</th>
                  <th className="py-2.5 px-3">Median Engagement Rate</th>
                  <th className="py-2.5 px-3">Vs Account Baseline</th>
                  <th className="py-2.5 px-3">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {durations.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-slate-500">No duration performance data recorded yet.</td>
                  </tr>
                ) : (
                  durations.map((dur, i) => (
                    <tr key={i} className="hover:bg-slate-800/30">
                      <td className="py-2.5 px-3 font-semibold text-slate-200">{dur.bucket}</td>
                      <td className="py-2.5 px-3">{dur.sample_size} clips</td>
                      <td className="py-2.5 px-3 font-medium text-slate-100">{dur.median_engagement_rate != null ? `${dur.median_engagement_rate}%` : '—'}</td>
                      <td className="py-2.5 px-3">
                        {dur.performance_vs_baseline_pct != null ? (
                          <span className={`font-semibold flex items-center gap-1 ${dur.performance_vs_baseline_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {dur.performance_vs_baseline_pct >= 0 ? '+' : ''}{dur.performance_vs_baseline_pct}%
                          </span>
                        ) : '—'}
                      </td>
                      <td className="py-2.5 px-3">{getConfidenceBadge(dur.confidence)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'windows' && (
        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-primary" />
              Localized Optimal Posting Windows
            </h3>
            <span className="text-xs text-slate-500">Account Timezone Resolved</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {windows.length === 0 ? (
              <div className="col-span-3 py-6 text-center text-slate-500">No localized posting window recommendations yet.</div>
            ) : (
              windows.map((win, i) => (
                <div key={i} className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-200 text-xs">{win.day_of_week}</span>
                    <span className="text-[11px] font-mono text-primary bg-primary/10 px-2 py-0.5 rounded">{win.hour_bucket}</span>
                  </div>
                  <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1 border-t border-slate-900">
                    <span>Sample: <strong className="text-slate-300">{win.sample_size}</strong></span>
                    <span>Median ER: <strong className="text-emerald-400">{win.median_engagement_rate}%</strong></span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {activeTab === 'gaps' && (
        <div className="space-y-4">
          {gaps.length === 0 ? (
            <div className="text-center py-12 bg-slate-900/40 border border-slate-800/80 rounded-2xl">
              <CheckCircle2 className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-sm font-medium text-slate-300">No content gaps discovered</p>
              <p className="text-xs text-slate-500 mt-1">Your high-performing topics have balanced format distribution.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {gaps.map((gap, i) => (
                <div key={i} className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-200 capitalize">Topic: {gap.topic.replace(/-/g, ' ')}</span>
                    <span className="px-2 py-0.5 bg-primary/10 text-primary text-[11px] font-semibold rounded border border-primary/20">
                      Missing {gap.missing_format}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">{gap.opportunity_reason}</p>
                  <div className="pt-2">
                    <Link
                      href={`/carousel?topic=${encodeURIComponent(gap.topic)}`}
                      className="inline-flex items-center justify-center gap-1.5 w-full py-2 px-3.5 bg-primary text-slate-950 font-semibold text-xs rounded-xl hover:bg-primary/90 transition-colors"
                    >
                      <Layers className="w-3.5 h-3.5" />
                      <span>Create Carousel on '{gap.topic.replace(/-/g, ' ')}'</span>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'experiments' && (
        <div className="space-y-4">
          {experiments.length === 0 ? (
            <div className="text-center py-12 bg-slate-900/40 border border-slate-800/80 rounded-2xl">
              <FlaskConical className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-sm font-medium text-slate-300">No active experiments</p>
              <p className="text-xs text-slate-500 mt-1">Experiments will be generated as more pattern data is gathered.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {experiments.map((exp) => (
                <div key={exp.id} className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-slate-100">{exp.title}</h4>
                    <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 text-[11px] font-semibold rounded border border-emerald-500/20">
                      {exp.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed font-mono text-[11px] bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                    Hypothesis: {exp.hypothesis}
                  </p>
                  <div className="grid grid-cols-2 gap-2 text-xs text-slate-400 pt-1">
                    <div>Tested Variable: <strong className="text-slate-200">{exp.variable_tested}</strong></div>
                    <div>Control Baseline: <strong className="text-slate-200">{exp.control_baseline != null ? `${exp.control_baseline}%` : '—'}</strong></div>
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800/80">
                    <span>Progress: <strong className="text-slate-200">{exp.current_sample_size ?? 0}/{exp.target_sample_size ?? 5}</strong> posts</span>
                    <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-primary" 
                        style={{ width: `${Math.min(100, ((exp.current_sample_size ?? 0) / (exp.target_sample_size ?? 5)) * 100)}%` }} 
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
