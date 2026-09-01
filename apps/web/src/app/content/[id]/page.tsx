"use client";

import React, { useState, useEffect, useRef, Suspense } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft, Video, Image as ImageIcon, FileText, Layers, Play, Pause,
  Search, Copy, Check, Sparkles, Scissors, Calendar, ShieldCheck, AlertTriangle,
  BarChart3, RefreshCw, Download, ExternalLink, Plus, Clock, FileCode, CheckCircle2,
  XCircle, Edit3, Save, Trash2, ChevronRight
} from 'lucide-react';
import { ContentItem, ClipItem, CarouselItem, PublicationItem } from '@/types';
import { api, API_BASE } from '@/lib/api';

function ContentWorkspaceContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const contentId = params?.id as string;
  const initialTab = searchParams?.get('tab') || 'overview';

  const [content, setContent] = useState<ContentItem | null>(null);
  const [activeTab, setActiveTab] = useState<string>(initialTab);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Sub-data states
  const [clips, setClips] = useState<ClipItem[]>([]);
  const [carousels, setCarousels] = useState<CarouselItem[]>([]);
  const [publications, setPublications] = useState<PublicationItem[]>([]);
  const [governance, setGovernance] = useState<any | null>(null);
  const [analytics, setAnalytics] = useState<any | null>(null);
  const [transcriptSearch, setTranscriptSearch] = useState<string>('');
  const [copiedText, setCopiedText] = useState<string | null>(null);

  // Video player ref
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  useEffect(() => {
    if (contentId) {
      loadWorkspaceData();
    }
  }, [contentId]);

  const loadWorkspaceData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getContent(contentId);
      setContent(res);

      // Load sub-entity collections concurrently
      const [clipsRes, carouselsRes, pubsRes, govRes, anaRes] = await Promise.allSettled([
        api.getContentClips(contentId),
        api.getCarousels(contentId),
        api.getPublications(contentId),
        api.getGovernanceResult(contentId),
        api.getContentAnalytics()
      ]);

      if (clipsRes.status === 'fulfilled') setClips(clipsRes.value.items || []);
      if (carouselsRes.status === 'fulfilled') setCarousels(carouselsRes.value.items || []);
      if (pubsRes.status === 'fulfilled') setPublications(pubsRes.value.items || []);
      if (govRes.status === 'fulfilled') setGovernance(govRes.value);
      if (anaRes.status === 'fulfilled') setAnalytics(anaRes.value);

    } catch (err: any) {
      setError(err.message || "Failed to load content workspace");
    } fontally: {
      setLoading(false);
    }
  };

  const handleSeek = (seconds: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = seconds;
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(label);
    setTimeout(() => setCopiedText(null), 2000);
  };

  if (loading) {
    return (
      <div className="p-8 max-w-7xl mx-auto space-y-6">
        <div className="h-8 w-48 bg-slate-800 animate-pulse rounded-lg" />
        <div className="h-40 w-full bg-slate-850 animate-pulse rounded-2xl" />
        <div className="h-96 w-full bg-slate-850 animate-pulse rounded-2xl" />
      </div>
    );
  }

  if (error || !content) {
    return (
      <div className="p-12 text-center max-w-xl mx-auto my-12 bg-slate-900 border border-slate-800 rounded-2xl">
        <AlertTriangle className="w-12 h-12 text-rose-400 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">Content Workspace Error</h2>
        <p className="text-sm text-slate-400 mb-6">{error || "Content item not found"}</p>
        <Link href="/content" className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold">
          Return to Content Library
        </Link>
      </div>
    );
  }

  const primaryAsset = content.assets?.[0];
  const primaryTranscript = content.transcripts?.[0];
  const primaryBrief = content.briefs?.[0];

  const videoStreamUrl = primaryAsset ? `${API_BASE}/api/content/${content.id}/asset/${primaryAsset.id}` : null;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Breadcrumb & Actions */}
      <div className="flex items-center justify-between">
        <Link href="/content" className="inline-flex items-center gap-2 text-xs text-slate-400 hover:text-white transition">
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Content Library</span>
        </Link>

        <div className="flex items-center gap-2">
          <button
            onClick={loadWorkspaceData}
            className="p-2 text-slate-400 hover:text-white bg-slate-800/60 border border-slate-700/60 rounded-xl text-xs flex items-center gap-1.5"
            title="Refresh workspace data"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Sync</span>
          </button>
        </div>
      </div>

      {/* 1. Header & Source Overview Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 text-xs font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded-full uppercase">
                {content.content_type}
              </span>
              <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-full border ${
                content.status === 'READY' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' :
                content.status === 'PROCESSING' ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' :
                'bg-slate-800 text-slate-400 border-slate-700'
              }`}>
                {content.status}
              </span>
              {governance && (
                <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-full border ${
                  governance.status === 'PASS' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' :
                  governance.status === 'PASS_WITH_WARNINGS' ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' :
                  'bg-rose-500/20 text-rose-300 border-rose-500/30'
                }`}>
                  Governance: {governance.status}
                </span>
              )}
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">{content.title}</h1>
            <p className="text-xs text-slate-400">
              Created {new Date(content.created_at || '').toLocaleDateString()} • ID: <code className="font-mono text-slate-300">{content.id}</code>
            </p>
          </div>

          {/* Smart Repurpose Action Bar */}
          <div className="flex flex-wrap items-center gap-2 bg-slate-850/80 p-2 rounded-xl border border-slate-800">
            <button
              onClick={() => router.push(`/repurpose?content_id=${content.id}`)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition"
            >
              <Scissors className="w-3.5 h-3.5" />
              <span>Create Clip</span>
            </button>
            <button
              onClick={() => router.push(`/carousel?content_id=${content.id}`)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-medium transition"
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Create Carousel</span>
            </button>
            <button
              onClick={() => router.push(`/calendar?content_id=${content.id}`)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-medium transition"
            >
              <Calendar className="w-3.5 h-3.5" />
              <span>Schedule</span>
            </button>
          </div>
        </div>

        {/* 2. Canonical Lifecycle Timeline */}
        <div className="mt-6 pt-6 border-t border-slate-800">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-3">Content Lifecycle Stage</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2">
            {[
              { label: 'Uploaded', active: true, done: true },
              { label: 'Processed', active: content.status === 'READY', done: content.status === 'READY' },
              { label: 'Repurposed', active: clips.length > 0 || carousels.length > 0, done: clips.length > 0 || carousels.length > 0 },
              { label: 'Reviewed', active: true, done: true },
              { label: 'Approved', active: publications.some(p => p.status === 'SCHEDULED' || p.status === 'PUBLISHED'), done: publications.some(p => p.status === 'SCHEDULED' || p.status === 'PUBLISHED') },
              { label: 'Published', active: publications.some(p => p.status === 'PUBLISHED'), done: publications.some(p => p.status === 'PUBLISHED') },
              { label: 'Analyzed', active: !!analytics, done: !!analytics }
            ].map((stage, idx) => (
              <div key={stage.label} className={`p-2.5 rounded-xl border text-center transition ${
                stage.done
                  ? 'bg-indigo-600/10 border-indigo-500/30 text-indigo-300'
                  : 'bg-slate-850/40 border-slate-800 text-slate-500'
              }`}>
                <div className="text-[10px] font-mono text-slate-500 mb-0.5">Step {idx + 1}</div>
                <div className="text-xs font-semibold truncate">{stage.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="border-b border-slate-800 flex items-center space-x-2 overflow-x-auto pb-1">
        {[
          { id: 'overview', label: 'Preview & Transcript' },
          { id: 'clips', label: `Clips (${clips.length})` },
          { id: 'carousels', label: `Carousels (${carousels.length})` },
          { id: 'copy', label: `Platform Copy (${content.generated_contents?.length || 0})` },
          { id: 'governance', label: 'Governance & Quality' },
          { id: 'publications', label: `Publications (${publications.length})` },
          { id: 'analytics', label: 'Performance Analytics' }
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-4 py-2.5 text-xs font-semibold rounded-t-xl transition whitespace-nowrap ${
              activeTab === t.id
                ? 'bg-slate-800 text-white border-t-2 border-indigo-500 shadow-md'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850/50'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* TAB CONTENT PANELS */}

      {/* TAB 1: PREVIEW & TRANSCRIPT */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Media Player Column */}
          <div className="lg:col-span-7 space-y-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-lg p-4">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center justify-between">
                <span>Source Asset Preview</span>
                {primaryAsset && (
                  <span className="text-xs text-slate-400 font-mono">
                    {primaryAsset.width}x{primaryAsset.height} • {primaryAsset.duration}s
                  </span>
                )}
              </h3>

              {content.content_type === 'VIDEO' && videoStreamUrl ? (
                <div className="relative rounded-xl overflow-hidden bg-black aspect-video flex items-center justify-center">
                  <video
                    ref={videoRef}
                    src={videoStreamUrl}
                    controls
                    className="w-full h-full object-contain"
                    onTimeUpdate={() => setCurrentTime(videoRef.current?.currentTime || 0)}
                  />
                </div>
              ) : content.content_type === 'IMAGE' && primaryAsset ? (
                <div className="rounded-xl overflow-hidden bg-slate-950 flex items-center justify-center p-4">
                  <img
                    src={`${API_BASE}/api/content/${content.id}/asset/${primaryAsset.id}`}
                    alt={content.title}
                    className="max-h-96 object-contain rounded-lg"
                  />
                </div>
              ) : content.content_type === 'TEXT' ? (
                <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-slate-200 text-sm font-mono whitespace-pre-wrap max-h-96 overflow-y-auto">
                  {content.text_content || "No raw text content available."}
                </div>
              ) : (
                <div className="p-8 text-center text-slate-500">Preview player unavailable for this content type.</div>
              )}
            </div>

            {/* Brief Summary Box */}
            {primaryBrief && (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-400" />
                  <span>AI Content Brief Summary</span>
                </h3>
                <p className="text-xs text-slate-300 leading-relaxed">{primaryBrief.summary}</p>
                <div className="flex flex-wrap gap-1.5 pt-2">
                  {primaryBrief.topics?.map(t => (
                    <span key={t} className="px-2 py-0.5 text-[10px] bg-slate-800 text-slate-300 rounded-md border border-slate-700">
                      #{t}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Interactive Transcript Column */}
          <div className="lg:col-span-5 space-y-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col h-[520px]">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <h3 className="text-sm font-semibold text-white">Interactive Transcript</h3>
                {primaryTranscript && (
                  <button
                    onClick={() => copyToClipboard(primaryTranscript.text, 'transcript')}
                    className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                  >
                    {copiedText === 'transcript' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedText === 'transcript' ? 'Copied' : 'Copy'}</span>
                  </button>
                )}
              </div>

              {primaryTranscript ? (
                <>
                  <div className="py-2">
                    <div className="relative">
                      <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        value={transcriptSearch}
                        onChange={(e) => setTranscriptSearch(e.target.value)}
                        placeholder="Search transcript..."
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none"
                      />
                    </div>
                  </div>

                  <div className="flex-1 overflow-y-auto space-y-2 pr-1 pt-1">
                    {primaryTranscript.segments
                      ?.filter(s => !transcriptSearch || s.text.toLowerCase().includes(transcriptSearch.toLowerCase()))
                      .map((seg, i) => (
                        <div
                          key={i}
                          onClick={() => handleSeek(seg.start_time)}
                          className="p-2.5 rounded-xl bg-slate-850/60 hover:bg-indigo-600/10 hover:border-indigo-500/40 border border-transparent cursor-pointer transition flex gap-3 group"
                        >
                          <span className="text-[11px] font-mono text-indigo-400 hover:underline flex-shrink-0">
                            {Math.floor(seg.start_time / 60)}:{String(Math.floor(seg.start_time % 60)).padStart(2, '0')}
                          </span>
                          <p className="text-xs text-slate-300 group-hover:text-white leading-relaxed">{seg.text}</p>
                        </div>
                      ))}
                  </div>
                </>
              ) : (
                <div className="flex-1 flex items-center justify-center text-center p-6 text-slate-500 text-xs">
                  Transcript unavailable for this source item.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: CLIPS */}
      {activeTab === 'clips' && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-white">Generated Short-Form Clips</h3>
            <button
              onClick={() => router.push(`/repurpose?content_id=${content.id}`)}
              className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Discover New Clips</span>
            </button>
          </div>

          {clips.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs">No clips generated yet. Use the Repurpose Studio to discover viral moments.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {clips.map(c => (
                <div key={c.id} className="p-4 bg-slate-850 rounded-xl border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-white truncate">{c.title || 'Untitled Clip'}</span>
                    <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-300 rounded font-mono text-[10px]">
                      {c.duration}s
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 italic font-serif">"{c.hook}"</p>
                  <div className="flex items-center justify-between pt-2 border-t border-slate-800 text-xs">
                    <span className="text-slate-500 font-mono text-[10px]">Score: {c.score || c.quality_score || 85}/100</span>
                    <button
                      onClick={() => router.push(`/repurpose?clip_id=${c.id}`)}
                      className="text-indigo-400 hover:underline font-medium text-xs"
                    >
                      Edit Clip →
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: CAROUSELS */}
      {activeTab === 'carousels' && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-white">Generated Carousel Decks</h3>
            <button
              onClick={() => router.push(`/carousel?content_id=${content.id}`)}
              className="px-3.5 py-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-semibold transition flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create Carousel</span>
            </button>
          </div>

          {carousels.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs">No carousel decks created yet.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {carousels.map(car => (
                <div key={car.id} className="p-4 bg-slate-850 rounded-xl border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-white">{car.title}</h4>
                    <span className="text-xs text-slate-400">{car.slide_count} Slides</span>
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t border-slate-800 text-xs">
                    <span className="text-slate-500 text-[10px]">{car.template} Template</span>
                    <button
                      onClick={() => router.push(`/carousel?carousel_id=${car.id}`)}
                      className="text-purple-400 hover:underline font-medium text-xs"
                    >
                      Open Studio →
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: PLATFORM COPY */}
      {activeTab === 'copy' && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <h3 className="text-base font-semibold text-white">Platform-Specific Copy Variants</h3>
          {content.generated_contents?.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs">No platform copy generated yet.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {content.generated_contents?.map(gc => (
                <div key={gc.id} className="p-4 bg-slate-850 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="px-2.5 py-0.5 text-[10px] font-bold bg-indigo-500/20 text-indigo-300 rounded uppercase">
                      {gc.platform}
                    </span>
                    <button
                      onClick={() => copyToClipboard(gc.payload?.text || gc.payload?.caption || '', gc.id)}
                      className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                    >
                      {copiedText === gc.id ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedText === gc.id ? 'Copied' : 'Copy Text'}</span>
                    </button>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap line-clamp-6">
                    {gc.payload?.text || gc.payload?.caption || JSON.stringify(gc.payload)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 5: GOVERNANCE */}
      {activeTab === 'governance' && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <h3 className="text-base font-semibold text-white">Governance & Quality Checks</h3>
          {governance ? (
            <div className="space-y-4">
              <div className="p-4 bg-slate-850 rounded-xl border border-slate-800 flex items-center justify-between">
                <div>
                  <div className="text-xs text-slate-400">Overall Governance Status</div>
                  <div className="text-lg font-bold text-white mt-0.5">{governance.status}</div>
                </div>
                <div className="flex gap-4 text-xs">
                  <div><span className="text-rose-400 font-bold">{governance.blocking_count}</span> Blocking</div>
                  <div><span className="text-amber-400 font-bold">{governance.warning_count}</span> Warnings</div>
                  <div><span className="text-emerald-400 font-bold">{governance.info_count}</span> Info</div>
                </div>
              </div>
            </div>
          ) : (
            <div className="py-12 text-center text-slate-500 text-xs">No governance checks performed yet.</div>
          )}
        </div>
      )}

      {/* TAB 6: PUBLICATIONS */}
      {activeTab === 'publications' && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-white">Publications</h3>
            <button
              onClick={() => router.push(`/publishing`)}
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold"
            >
              Open Publishing Queue
            </button>
          </div>

          {publications.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs">No publication records for this content item.</div>
          ) : (
            <div className="space-y-2">
              {publications.map(p => (
                <div key={p.id} className="p-3 bg-slate-850 rounded-xl border border-slate-800 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-3">
                    <span className="font-bold text-white uppercase">{p.platform}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] ${
                      p.status === 'PUBLISHED' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-800 text-slate-400'
                    }`}>
                      {p.status}
                    </span>
                  </div>
                  {p.external_url && (
                    <a href={p.external_url} target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline flex items-center gap-1">
                      <span>View External</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 7: ANALYTICS */}
      {activeTab === 'analytics' && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <h3 className="text-base font-semibold text-white">Asset Performance Metrics</h3>
          {analytics ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="p-4 bg-slate-850 rounded-xl border border-slate-800">
                <div className="text-xs text-slate-400">Total Views</div>
                <div className="text-xl font-bold text-white mt-1">{analytics.total_views || 0}</div>
              </div>
              <div className="p-4 bg-slate-850 rounded-xl border border-slate-800">
                <div className="text-xs text-slate-400">Total Engagements</div>
                <div className="text-xl font-bold text-white mt-1">{analytics.total_engagements || 0}</div>
              </div>
              <div className="p-4 bg-slate-850 rounded-xl border border-slate-800">
                <div className="text-xs text-slate-400">Engagement Rate</div>
                <div className="text-xl font-bold text-emerald-400 mt-1">{((analytics.engagement_rate || 0) * 100).toFixed(1)}%</div>
              </div>
              <div className="p-4 bg-slate-850 rounded-xl border border-slate-800">
                <div className="text-xs text-slate-400">Performance vs Baseline</div>
                <div className="text-xl font-bold text-indigo-400 mt-1">+{analytics.vs_baseline || 0}%</div>
              </div>
            </div>
          ) : (
            <div className="py-12 text-center text-slate-500 text-xs">Analytics sync pending publication.</div>
          )}
        </div>
      )}
    </div>
  );
}

export default function UnifiedContentWorkspacePage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-500">Loading content workspace...</div>}>
      <ContentWorkspaceContent />
    </Suspense>
  );
}
