"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { 
  GitBranch, 
  Play, 
  Plus, 
  Sparkles, 
  Filter, 
  Clock, 
  Share2, 
  CheckCircle2, 
  Zap,
  ArrowRight,
  Trash2,
  RefreshCw,
  AlertCircle,
  Eye,
  Settings,
  X,
  Volume2,
  Film,
  Calendar,
  Check,
  ExternalLink,
  ChevronRight,
  ChevronLeft,
  Search,
  Tag,
  Maximize2,
  Edit3,
  Video,
  Radio,
  FileText,
  Clock3,
  Lock,
  Globe,
  SlidersHorizontal,
  ChevronDown,
  Wand2,
  Layers,
  Flame,
  CheckCheck,
  Send,
  MoreVertical,
  Activity,
  Headphones,
  Sliders
} from 'lucide-react';
import { 
  YoutubeIcon, 
  InstagramIcon, 
  TiktokIcon, 
  LinkedinIcon, 
  XIcon, 
  FacebookIcon 
} from '@/components/ui/SocialIcons';
import { api } from '@/lib/api';
import { WorkflowItem, InboundSourceItem } from '@/types';

interface WorkflowContentItem {
  id: string;
  external_id: string;
  title: string;
  media_url: string;
  ingestion_status: string;
  content_id?: string | null;
  duration?: number | null;
  thumbnail?: string | null;
  detected_at?: string | null;
  publications: Array<{
    id: string;
    platform: string;
    status: string;
    scheduled_at?: string | null;
    published_at?: string | null;
    external_url?: string | null;
  }>;
}

interface WorkflowContentResponse {
  workflow_id: string;
  workflow_name: string;
  source_id?: string | null;
  mode: string;
  items: WorkflowContentItem[];
}

const QUICK_TAG_SUGGESTIONS = [
  '#repurpose', '#shorts', '#podcastclips', '#creatorgrowth', 
  '#entrepreneur', '#productivity', '#techleads', '#startups'
];

const PLATFORM_CHAR_LIMITS: Record<string, number> = {
  tiktok: 2200,
  instagram: 2200,
  youtube: 100, // Shorts title limit
  x: 280,
  linkedin: 3000,
  facebook: 63206
};

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<WorkflowItem[]>([]);
  const [sources, setSources] = useState<InboundSourceItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filterTab, setFilterTab] = useState<'all' | 'automatic' | 'approval'>('all');

  // Execution state
  const [runningWfId, setRunningWfId] = useState<string | null>(null);
  const [runningItemId, setRunningItemId] = useState<string | null>(null);
  const [executionResult, setExecutionResult] = useState<any | null>(null);

  // Repurpose.io "View Content" Episodes Drawer / Modal State
  const [selectedWorkflowForContent, setSelectedWorkflowForContent] = useState<WorkflowItem | null>(null);
  const [workflowContent, setWorkflowContent] = useState<WorkflowContentResponse | null>(null);
  const [isLoadingContent, setIsLoadingContent] = useState(false);
  const [contentSearchQuery, setContentSearchQuery] = useState('');
  const [contentStatusFilter, setContentStatusFilter] = useState<'ALL' | 'PUBLISHED' | 'QUEUED' | 'READY'>('ALL');

  // Custom Caption & Multi-Platform Drawer State
  const [captionItem, setCaptionItem] = useState<WorkflowContentItem | null>(null);
  const [customCaptionText, setCustomCaptionText] = useState('');
  const [activeCaptionPreviewPlatform, setActiveCaptionPreviewPlatform] = useState<string>('tiktok');

  // 5-Step Creation Wizard State
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4 | 5>(1);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State
  const [wfName, setWfName] = useState('');
  const [wfDesc, setWfDesc] = useState('');
  const [wfSourceId, setWfSourceId] = useState('');
  const [wfMode, setWfMode] = useState<'AUTOMATIC' | 'APPROVAL_REQUIRED'>('AUTOMATIC');
  const [includeTags, setIncludeTags] = useState('#repurpose, #shorts');
  const [excludeTags, setExcludeTags] = useState('#sponsor, #ad');
  const [actionType, setActionType] = useState<'AI_CLIPS' | 'AUDIOGRAM' | 'FULL_VIDEO'>('AI_CLIPS');
  const [aspectRatio, setAspectRatio] = useState('9:16');
  const [waveformStyle, setWaveformStyle] = useState<'BARS' | 'LINE' | 'CIRCULAR' | 'WAVE'>('BARS');
  const [waveformColor, setWaveformColor] = useState('#6366F1');
  const [stripWatermark, setStripWatermark] = useState(true);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['youtube', 'instagram', 'tiktok']);
  const [captionTemplate, setCaptionTemplate] = useState('{{title}}\n\nTake your audience from zero to one with automated syndication.\n\n#shorts #repurpose #creator');
  const [dripEnabled, setDripEnabled] = useState(true);
  const [dripInterval, setDripInterval] = useState(4);
  const [activeHoursStart, setActiveHoursStart] = useState(9);
  const [activeHoursEnd, setActiveHoursEnd] = useState(21);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [wfs, srcs] = await Promise.all([
        api.getWorkflows(),
        api.getInboundSources()
      ]);
      setWorkflows(wfs || []);
      setSources(srcs || []);
      if (srcs && srcs.length > 0 && !wfSourceId) {
        setWfSourceId(srcs[0].id);
      }
    } catch (err) {
      console.error("Failed to load workflows/sources:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleMode = async (wf: WorkflowItem) => {
    const newMode = wf.mode === 'AUTOMATIC' ? 'APPROVAL_REQUIRED' : 'AUTOMATIC';
    try {
      await api.updateWorkflow(wf.id, { mode: newMode });
      setWorkflows(prev => prev.map(w => w.id === wf.id ? { ...w, mode: newMode } : w));
    } catch (err) {
      console.error("Failed to toggle workflow mode:", err);
    }
  };

  const handleToggleActive = async (wf: WorkflowItem) => {
    try {
      await api.updateWorkflow(wf.id, { active: !wf.active });
      setWorkflows(prev => prev.map(w => w.id === wf.id ? { ...w, active: !w.active } : w));
    } catch (err) {
      console.error("Failed to toggle workflow:", err);
    }
  };

  const handleRunWorkflow = async (workflowId: string, feedItemId?: string, captionOverride?: string) => {
    if (feedItemId) {
      setRunningItemId(feedItemId);
    } else {
      setRunningWfId(workflowId);
    }
    setExecutionResult(null);

    try {
      const result = await api.runWorkflow(workflowId, {
        feed_item_id: feedItemId,
        custom_caption: captionOverride
      });
      setExecutionResult(result);

      if (selectedWorkflowForContent && selectedWorkflowForContent.id === workflowId) {
        await loadWorkflowContent(workflowId);
      }
      await loadData();
    } catch (err: any) {
      setExecutionResult({
        status: "failed",
        error: err.message || "Workflow execution failed."
      });
    } finally {
      setRunningWfId(null);
      setRunningItemId(null);
      setCaptionItem(null);
    }
  };

  const handleDeleteWorkflow = async (id: string) => {
    if (!confirm("Are you sure you want to delete this workflow?")) return;
    try {
      await api.deleteWorkflow(id);
      setWorkflows(prev => prev.filter(w => w.id !== id));
      if (selectedWorkflowForContent?.id === id) {
        setSelectedWorkflowForContent(null);
        setWorkflowContent(null);
      }
    } catch (err) {
      console.error("Failed to delete workflow:", err);
    }
  };

  // Repurpose.io "View Content" Episodes Loader
  const handleOpenContent = async (wf: WorkflowItem) => {
    setSelectedWorkflowForContent(wf);
    await loadWorkflowContent(wf.id);
  };

  const loadWorkflowContent = async (workflowId: string) => {
    setIsLoadingContent(true);
    try {
      const content = await api.getWorkflowContent(workflowId);
      setWorkflowContent(content);
    } catch (err) {
      console.error("Failed to load workflow content:", err);
    } finally {
      setIsLoadingContent(false);
    }
  };

  // Quick Start Template Applier
  const applyQuickTemplate = (templateType: 'PODCAST' | 'SHORTS' | 'AUDIOGRAM') => {
    if (templateType === 'PODCAST') {
      setWfName('Podcast to Viral Short Clips');
      setWfDesc('Auto-detect high-impact conversational hooks & transcode to vertical video.');
      setActionType('AI_CLIPS');
      setAspectRatio('9:16');
      setSelectedPlatforms(['tiktok', 'instagram', 'youtube']);
      setDripInterval(4);
    } else if (templateType === 'SHORTS') {
      setWfName('TikTok to YouTube Shorts & Reels');
      setWfDesc('Strip TikTok watermarks cleanly and distribute across Meta & Google.');
      setActionType('FULL_VIDEO');
      setAspectRatio('9:16');
      setStripWatermark(true);
      setSelectedPlatforms(['youtube', 'instagram']);
      setDripInterval(3);
    } else {
      setWfName('Audio Episode to Neon Audiogram');
      setWfDesc('Generate pulsating soundwave visuals for social feeds from raw audio.');
      setActionType('AUDIOGRAM');
      setAspectRatio('1:1');
      setWaveformStyle('BARS');
      setWaveformColor('#6366F1');
      setSelectedPlatforms(['linkedin', 'instagram']);
      setDripInterval(6);
    }
  };

  // 5-Step Creation Wizard Submit
  const handleCreateWorkflow = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!wfName.trim()) return;

    setIsSubmitting(true);
    try {
      const inc = includeTags.split(',').map(s => s.trim()).filter(Boolean);
      const exc = excludeTags.split(',').map(s => s.trim()).filter(Boolean);

      const dests = selectedPlatforms.map(plat => ({
        platform: plat,
        privacy: 'PUBLIC' as const,
        custom_caption: captionTemplate
      }));

      await api.createWorkflow({
        name: wfName,
        description: wfDesc,
        active: true,
        trigger: wfSourceId ? "Source Ingestion" : "Manual Upload",
        source_id: wfSourceId || null,
        mode: wfMode,
        filters: {
          include_hashtags: inc,
          exclude_hashtags: exc
        },
        actions_config: {
          action_type: actionType,
          aspect_ratio: aspectRatio,
          aspect_ratios: [aspectRatio],
          waveform_style: waveformStyle,
          waveform_color: waveformColor,
          strip_watermark: stripWatermark
        },
        destinations: dests,
        drip_config: {
          drip_enabled: dripEnabled,
          interval_hours: dripInterval,
          active_hours_start: activeHoursStart,
          active_hours_end: activeHoursEnd
        }
      });

      setIsWizardOpen(false);
      resetWizard();
      await loadData();
    } catch (err) {
      console.error("Failed to create workflow:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetWizard = () => {
    setCurrentStep(1);
    setWfName('');
    setWfDesc('');
    setWfMode('AUTOMATIC');
    setIncludeTags('#repurpose, #shorts');
    setExcludeTags('#sponsor, #ad');
    setActionType('AI_CLIPS');
    setAspectRatio('9:16');
    setDripEnabled(true);
    setDripInterval(4);
  };

  const filteredWorkflows = workflows.filter(w => {
    if (filterTab === 'automatic') return w.mode === 'AUTOMATIC';
    if (filterTab === 'approval') return w.mode === 'APPROVAL_REQUIRED';
    return true;
  });

  const getPlatformIcon = (platform: string) => {
    const p = platform.toLowerCase();
    if (p.includes('youtube')) return <YoutubeIcon className="w-4 h-4 text-[#FF0000]" />;
    if (p.includes('instagram')) return <InstagramIcon className="w-4 h-4 text-[#E1306C]" />;
    if (p.includes('tiktok')) return <TiktokIcon className="w-4 h-4 text-[#00F2FE]" />;
    if (p.includes('linkedin')) return <LinkedinIcon className="w-4 h-4 text-[#0A66C2]" />;
    if (p.includes('facebook')) return <FacebookIcon className="w-4 h-4 text-[#1877F2]" />;
    if (p.includes('x') || p.includes('twitter')) return <XIcon className="w-4 h-4 text-white" />;
    return <Share2 className="w-4 h-4 text-gray-400" />;
  };

  // Filtered Episodes inside View Content Drawer
  const filteredEpisodes = useMemo(() => {
    if (!workflowContent?.items) return [];
    return workflowContent.items.filter(item => {
      const matchesSearch = item.title.toLowerCase().includes(contentSearchQuery.toLowerCase());
      if (!matchesSearch) return false;

      const hasPub = item.publications && item.publications.length > 0;
      const isPublished = hasPub && item.publications.some(p => p.status === 'PUBLISHED');
      const isQueued = hasPub && item.publications.some(p => p.status === 'SCHEDULED' || p.status === 'QUEUED');

      if (contentStatusFilter === 'PUBLISHED') return isPublished;
      if (contentStatusFilter === 'QUEUED') return isQueued;
      if (contentStatusFilter === 'READY') return !isPublished && !isQueued;

      return true;
    });
  }, [workflowContent, contentSearchQuery, contentStatusFilter]);

  return (
    <div className="space-y-8 animate-fadeIn pb-20">
      {/* Editorial Header */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-5 border-b border-white/[0.06] pb-6">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-widest bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-semibold">
              Distribution Engine
            </span>
            <span className="text-xs text-gray-500 font-mono">•</span>
            <span className="text-xs text-gray-400 font-medium">Repurpose.io Pipeline Suite</span>
          </div>
          <h1 className="text-3xl font-bold font-display text-white tracking-tight">
            Autonomous Workflows
          </h1>
          <p className="text-sm text-gray-400 max-w-2xl leading-relaxed">
            Ingest podcasts and videos once. Generate vertical hooks, soundwaves, and subtitles, then drip natively across TikTok, Reels, Shorts, and LinkedIn.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={loadData}
            className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.08] text-gray-300 text-xs font-medium transition-all shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Sync Engine</span>
          </button>
          <button
            onClick={() => {
              resetWizard();
              setIsWizardOpen(true);
            }}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 via-indigo-600 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white text-xs font-semibold shadow-lg shadow-indigo-500/25 transition-all transform hover:-translate-y-0.5"
          >
            <Plus className="w-4 h-4" />
            <span>New Workflow</span>
          </button>
        </div>
      </div>

      {/* Creator Metrics Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="surface-card p-4 rounded-2xl relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400 font-medium">Active Pipelines</span>
            <div className="w-7 h-7 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400">
              <GitBranch className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-2xl font-bold font-display text-white mt-2">
            {workflows.filter(w => w.active).length}
            <span className="text-xs text-gray-500 font-normal ml-1.5 font-mono">/ {workflows.length} total</span>
          </div>
          <div className="text-[11px] text-gray-400 mt-1 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>Polling sources every 15m</span>
          </div>
        </div>

        <div className="surface-card p-4 rounded-2xl relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400 font-medium">Auto-Publish Channels</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
              <Zap className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-2xl font-bold font-display text-emerald-400 mt-2">
            {workflows.filter(w => w.mode === 'AUTOMATIC' && w.active).length}
          </div>
          <div className="text-[11px] text-gray-400 mt-1">
            Zero-touch autonomous syndication
          </div>
        </div>

        <div className="surface-card p-4 rounded-2xl relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400 font-medium">Manual Review Staging</span>
            <div className="w-7 h-7 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400">
              <Lock className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-2xl font-bold font-display text-amber-300 mt-2">
            {workflows.filter(w => w.mode === 'APPROVAL_REQUIRED').length}
          </div>
          <div className="text-[11px] text-gray-400 mt-1">
            Held in View Content for review
          </div>
        </div>

        <div className="surface-card p-4 rounded-2xl relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400 font-medium">Episodes Syndicated</span>
            <div className="w-7 h-7 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400">
              <Film className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-2xl font-bold font-display text-purple-300 mt-2">
            {workflows.reduce((acc, w) => acc + (w.execution_count || 0), 0)}
          </div>
          <div className="text-[11px] text-gray-400 mt-1">
            Across YouTube, Reels & TikTok
          </div>
        </div>
      </div>

      {/* Execution Feedback Notification Banner */}
      {executionResult && (
        <div className={`p-4 rounded-2xl border transition-all ${
          executionResult.status === 'succeeded' 
            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' 
            : executionResult.status === 'skipped'
            ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
            : 'bg-red-500/10 border-red-500/30 text-red-300'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              {executionResult.status === 'succeeded' ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              ) : (
                <AlertCircle className="w-5 h-5 text-amber-400" />
              )}
              <div>
                <span className="text-xs font-semibold block">
                  {executionResult.status === 'succeeded' 
                    ? `Workflow run executed successfully! Generated ${executionResult.publications_count || 0} scheduled publication(s).`
                    : executionResult.reason || executionResult.message || executionResult.error || "Workflow completed."}
                </span>
                {executionResult.execution_id && (
                  <span className="text-[10px] opacity-75 font-mono">Trace ID: {executionResult.execution_id}</span>
                )}
              </div>
            </div>
            <button 
              onClick={() => setExecutionResult(null)}
              className="p-1 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* View Filters Filter Tab Bar */}
      <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-white/[0.03] border border-white/[0.06]">
          {(['all', 'automatic', 'approval'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setFilterTab(tab)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                filterTab === tab
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab === 'all' && `All Workflows (${workflows.length})`}
              {tab === 'automatic' && `Auto-Publish (${workflows.filter(w => w.mode === 'AUTOMATIC').length})`}
              {tab === 'approval' && `Manual Review (${workflows.filter(w => w.mode === 'APPROVAL_REQUIRED').length})`}
            </button>
          ))}
        </div>
      </div>

      {/* Workflows Node-Graph List */}
      {filteredWorkflows.length === 0 ? (
        <div className="surface-card rounded-3xl p-12 text-center space-y-5 border-dashed">
          <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto text-indigo-400">
            <GitBranch className="w-7 h-7" />
          </div>
          <div className="max-w-md mx-auto space-y-1.5">
            <h3 className="text-lg font-bold font-display text-white">No active workflows found</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Create an automated repurpose pipeline to listen to your podcast RSS, YouTube channel, or local folder and syndicate clips to social channels.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <button
              onClick={() => {
                applyQuickTemplate('PODCAST');
                setIsWizardOpen(true);
              }}
              className="px-3.5 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-xs font-medium text-gray-300 transition-all flex items-center gap-2"
            >
              <Headphones className="w-3.5 h-3.5 text-indigo-400" />
              <span>Podcast to Viral Shorts</span>
            </button>
            <button
              onClick={() => {
                applyQuickTemplate('SHORTS');
                setIsWizardOpen(true);
              }}
              className="px-3.5 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-xs font-medium text-gray-300 transition-all flex items-center gap-2"
            >
              <Film className="w-3.5 h-3.5 text-emerald-400" />
              <span>TikTok to YouTube Shorts</span>
            </button>
            <button
              onClick={() => {
                applyQuickTemplate('AUDIOGRAM');
                setIsWizardOpen(true);
              }}
              className="px-3.5 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-xs font-medium text-gray-300 transition-all flex items-center gap-2"
            >
              <Volume2 className="w-3.5 h-3.5 text-purple-400" />
              <span>Audio to Neon Audiogram</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredWorkflows.map(wf => {
            const linkedSource = sources.find(s => s.id === wf.source_id);
            const isRunning = runningWfId === wf.id;

            return (
              <div 
                key={wf.id}
                className="surface-card surface-card-hover rounded-2xl p-5 space-y-4 shadow-md relative group"
              >
                {/* Header: Title, Description, Status, and Physical Auto/Manual Switch */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  <div className="flex items-center gap-3.5">
                    {/* Active Pipeline Toggle Switch */}
                    <button
                      onClick={() => handleToggleActive(wf)}
                      title={wf.active ? "Pause workflow" : "Activate workflow"}
                      className={`relative inline-flex h-5 w-10 shrink-0 cursor-pointer rounded-full border border-white/10 transition-colors duration-200 ease-in-out focus:outline-none ${
                        wf.active ? 'bg-indigo-600' : 'bg-gray-800'
                      }`}
                    >
                      <span
                        className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-md transition duration-200 ease-in-out ${
                          wf.active ? 'translate-x-5' : 'translate-x-0.5'
                        }`}
                      />
                    </button>

                    <div>
                      <div className="flex items-center gap-2.5">
                        <h3 className="text-base font-bold font-display text-white tracking-tight">{wf.name}</h3>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase tracking-wider border ${
                          wf.active 
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : 'bg-gray-500/10 text-gray-400 border-gray-500/20'
                        }`}>
                          {wf.active ? 'Active' : 'Paused'}
                        </span>
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5">{wf.description || "Automated multi-platform distribution pipeline."}</p>
                    </div>
                  </div>

                  {/* Tactile Repurpose.io Mode Pill Switch */}
                  <div className="flex items-center gap-3 self-end sm:self-center">
                    <div className="flex items-center p-1 rounded-xl bg-black/40 border border-white/[0.08] shadow-inner">
                      <button
                        onClick={() => wf.mode !== 'APPROVAL_REQUIRED' && handleToggleMode(wf)}
                        className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                          wf.mode === 'APPROVAL_REQUIRED'
                            ? 'bg-[#1E293B] text-amber-300 shadow-sm border border-amber-500/30'
                            : 'text-gray-400 hover:text-white'
                        }`}
                        title="Episodes require manual review before publishing"
                      >
                        <Lock className="w-3 h-3 text-amber-400" />
                        <span>Manual</span>
                      </button>
                      <button
                        onClick={() => wf.mode !== 'AUTOMATIC' && handleToggleMode(wf)}
                        className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                          wf.mode === 'AUTOMATIC'
                            ? 'bg-emerald-600 text-white shadow-sm border border-emerald-400/30'
                            : 'text-gray-400 hover:text-white'
                        }`}
                        title="Episodes are automatically dripped without human intervention"
                      >
                        <Zap className="w-3 h-3 text-emerald-200" />
                        <span>Auto</span>
                      </button>
                    </div>

                    <button
                      onClick={() => handleDeleteWorkflow(wf.id)}
                      className="p-2 rounded-xl text-gray-500 hover:text-red-400 hover:bg-white/[0.04] transition-all"
                      title="Delete pipeline"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Pipeline Flow Conduit Visualizer */}
                <div className="p-4 rounded-xl bg-[#080B11] border border-white/[0.05] flex flex-wrap items-center gap-3 text-xs">
                  {/* Source Node */}
                  <div className="flex items-center gap-2.5 px-3.5 py-2 rounded-xl bg-white/[0.03] border border-white/[0.08]">
                    <div className="w-7 h-7 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400 border border-amber-500/20">
                      <Radio className="w-3.5 h-3.5" />
                    </div>
                    <div>
                      <div className="text-[10px] text-gray-500 font-mono uppercase font-semibold">Inbound Source</div>
                      <div className="text-xs font-bold text-white truncate max-w-[150px]">
                        {linkedSource ? linkedSource.name : (wf.trigger || 'Manual Feed')}
                      </div>
                    </div>
                  </div>

                  <ArrowRight className="w-4 h-4 text-gray-600 shrink-0" />

                  {/* Transformation Action Node */}
                  <div className="flex items-center gap-2.5 px-3.5 py-2 rounded-xl bg-indigo-500/[0.06] border border-indigo-500/30 text-gray-200">
                    <div className="w-7 h-7 rounded-lg bg-indigo-500/20 flex items-center justify-center text-indigo-400 border border-indigo-500/30">
                      {wf.actions_config?.action_type === 'AUDIOGRAM' ? (
                        <Volume2 className="w-3.5 h-3.5" />
                      ) : (
                        <Sparkles className="w-3.5 h-3.5" />
                      )}
                    </div>
                    <div>
                      <div className="text-[10px] text-indigo-400 font-mono uppercase font-semibold">Transform Action</div>
                      <div className="text-xs font-bold text-white">
                        {wf.actions_config?.action_type || 'AI_CLIPS'} ({wf.actions_config?.aspect_ratio || '9:16'})
                      </div>
                    </div>
                  </div>

                  <ArrowRight className="w-4 h-4 text-gray-600 shrink-0" />

                  {/* Destination Nodes */}
                  <div className="flex items-center gap-2.5 px-3.5 py-2 rounded-xl bg-white/[0.03] border border-white/[0.08]">
                    <div>
                      <div className="text-[10px] text-gray-500 font-mono uppercase font-semibold">Destinations</div>
                      <div className="flex items-center gap-1.5 mt-1">
                        {wf.destinations?.map((d, i) => (
                          <span key={i} title={d.platform} className="p-1 rounded-md bg-black/40 border border-white/10">
                            {getPlatformIcon(d.platform)}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Drip Interval Badge */}
                  <div className="ml-auto flex items-center gap-2">
                    {wf.drip_config?.drip_enabled && (
                      <span className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono text-emerald-400 font-medium bg-emerald-500/10 border border-emerald-500/20">
                        <Clock className="w-3 h-3" />
                        <span>Drip: Every {wf.drip_config.interval_hours || 4}h</span>
                      </span>
                    )}
                    {wf.actions_config?.strip_watermark && (
                      <span className="px-2.5 py-1 rounded-lg text-xs font-mono text-purple-400 font-medium bg-purple-500/10 border border-purple-500/20">
                        ✓ No Watermark
                      </span>
                    )}
                  </div>
                </div>

                {/* Card Action Footer with Primary Repurpose.io "View Content" */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-2 border-t border-white/[0.05] text-xs text-gray-400">
                  <div className="flex items-center gap-4 text-[11px] font-mono">
                    <span>Processed: <strong className="text-white font-sans">{wf.execution_count || 0} episodes</strong></span>
                    <span>Last Synced: <strong className="text-gray-300 font-sans">{wf.last_run_at ? new Date(wf.last_run_at).toLocaleString() : 'Never'}</strong></span>
                  </div>

                  <div className="flex items-center gap-2.5">
                    {/* Primary Repurpose.io CTA: View Content */}
                    <button
                      onClick={() => handleOpenContent(wf)}
                      className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-md shadow-indigo-500/20 transition-all transform hover:-translate-y-0.5"
                    >
                      <Film className="w-3.5 h-3.5" />
                      <span>View Content</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>

                    {/* Quick Trigger Pipeline */}
                    <button
                      onClick={() => handleRunWorkflow(wf.id)}
                      disabled={isRunning || !wf.active}
                      className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-gray-300 text-xs font-medium transition-all disabled:opacity-40"
                    >
                      <Play className={`w-3.5 h-3.5 ${isRunning ? 'animate-spin' : ''}`} />
                      <span>{isRunning ? "Running..." : "Run Now"}</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ========================================================================= */}
      {/* REPURPOSE.IO "VIEW CONTENT" EPISODES DRAWER / STUDIO                      */}
      {/* ========================================================================= */}
      {selectedWorkflowForContent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/85 backdrop-blur-xl animate-fadeIn">
          <div className="surface-elevated rounded-3xl w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden border border-white/10">
            {/* Drawer Top Header */}
            <div className="p-5 border-b border-white/[0.08] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-[#080B11]">
              <div className="space-y-1">
                <div className="flex items-center gap-2.5">
                  <span className="text-[10px] font-mono uppercase tracking-widest font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-500/20">
                    Content Catalog
                  </span>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold border ${
                    selectedWorkflowForContent.mode === 'AUTOMATIC'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                  }`}>
                    {selectedWorkflowForContent.mode === 'AUTOMATIC' ? '⚡ Auto-Drip Active' : '🛡️ Manual Review Mode'}
                  </span>
                </div>
                <h2 className="text-xl font-bold font-display text-white">{selectedWorkflowForContent.name}</h2>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => loadWorkflowContent(selectedWorkflowForContent.id)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-gray-300 text-xs font-medium"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isLoadingContent ? 'animate-spin' : ''}`} />
                  <span>Sync Feed</span>
                </button>
                <button
                  onClick={() => {
                    setSelectedWorkflowForContent(null);
                    setWorkflowContent(null);
                  }}
                  className="p-1.5 rounded-xl text-gray-400 hover:text-white hover:bg-white/[0.08]"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Filter & Search Bar */}
            <div className="px-5 py-3 border-b border-white/[0.06] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-[#0B0E17]">
              <div className="flex items-center gap-1.5">
                {(['ALL', 'READY', 'QUEUED', 'PUBLISHED'] as const).map(f => (
                  <button
                    key={f}
                    onClick={() => setContentStatusFilter(f)}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                      contentStatusFilter === f
                        ? 'bg-indigo-600 text-white shadow-sm'
                        : 'text-gray-400 hover:text-white hover:bg-white/[0.04]'
                    }`}
                  >
                    {f === 'ALL' && 'All Episodes'}
                    {f === 'READY' && 'Ready / Unpublished'}
                    {f === 'QUEUED' && 'Queued (Drip)'}
                    {f === 'PUBLISHED' && 'Published'}
                  </button>
                ))}
              </div>

              <div className="relative w-full sm:w-64">
                <Search className="w-3.5 h-3.5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Filter by title..."
                  value={contentSearchQuery}
                  onChange={e => setContentSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-white text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            {/* Episodes List Body */}
            <div className="p-5 overflow-y-auto space-y-3 flex-1 bg-[#080B11]">
              {isLoadingContent ? (
                <div className="text-center py-20 text-gray-400 text-xs flex items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
                  <span>Fetching episodes from source channel...</span>
                </div>
              ) : filteredEpisodes.length === 0 ? (
                <div className="text-center py-20 surface-card rounded-2xl p-6 border-dashed">
                  <Film className="w-8 h-8 text-gray-500 mx-auto mb-2" />
                  <p className="text-sm font-semibold text-white">No episodes in feed</p>
                  <p className="text-xs text-gray-400 mt-1 max-w-sm mx-auto">
                    Ensure your podcast RSS or YouTube channel URL is valid, or upload manual files.
                  </p>
                </div>
              ) : (
                filteredEpisodes.map(item => {
                  const isItemRunning = runningItemId === item.id;
                  const publications = item.publications || [];
                  const isPublished = publications.some(p => p.status === 'PUBLISHED');
                  const isQueued = publications.some(p => p.status === 'SCHEDULED' || p.status === 'QUEUED');
                  const latestPub = publications[0];

                  return (
                    <div
                      key={item.id}
                      className="surface-card rounded-2xl p-4 hover:border-indigo-500/30 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
                    >
                      {/* Left: Thumbnail, Duration, Metadata */}
                      <div className="flex items-start gap-4">
                        <div className="w-20 h-16 rounded-xl bg-black/40 border border-white/10 shrink-0 flex items-center justify-center text-gray-400 relative overflow-hidden">
                          {item.thumbnail ? (
                            <img src={item.thumbnail} alt={item.title} className="w-full h-full object-cover" />
                          ) : (
                            <div className="flex flex-col items-center">
                              <Volume2 className="w-5 h-5 text-indigo-400" />
                              <span className="text-[9px] text-gray-500 font-mono mt-0.5">AUDIO</span>
                            </div>
                          )}
                          {item.duration && (
                            <span className="absolute bottom-1 right-1 bg-black/80 px-1 py-0.2 rounded text-[9px] text-gray-300 font-mono">
                              {Math.floor(item.duration / 60)}:{(item.duration % 60).toString().padStart(2, '0')}
                            </span>
                          )}
                        </div>

                        <div className="space-y-1">
                          <h4 className="text-sm font-bold text-white line-clamp-1">{item.title}</h4>
                          <div className="flex items-center gap-2 text-[11px] text-gray-400 font-mono">
                            <span>Detected: {item.detected_at ? new Date(item.detected_at).toLocaleDateString() : 'Recent'}</span>
                            {item.media_url && (
                              <>
                                <span>•</span>
                                <a
                                  href={item.media_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-sans"
                                >
                                  <span>Original Media</span>
                                  <ExternalLink className="w-3 h-3" />
                                </a>
                              </>
                            )}
                          </div>

                          {/* Live Publication Status Badges */}
                          <div className="flex items-center gap-2 pt-1">
                            {isPublished ? (
                              <div className="flex items-center gap-2">
                                <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                  <CheckCircle2 className="w-3 h-3" />
                                  <span>Published</span>
                                </span>
                                {latestPub?.external_url && (
                                  <a
                                    href={latestPub.external_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-[11px] text-emerald-400 hover:underline flex items-center gap-1 font-medium"
                                  >
                                    <span>View Post</span>
                                    <ExternalLink className="w-3 h-3" />
                                  </a>
                                )}
                              </div>
                            ) : isQueued ? (
                              <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/20">
                                <Clock className="w-3 h-3" />
                                <span>Drip: {latestPub?.scheduled_at ? new Date(latestPub.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Next Slot'}</span>
                              </span>
                            ) : (
                              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-white/[0.04] text-gray-400 border border-white/[0.08]">
                                Ready for Syndication
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Right: Actions for Episode */}
                      <div className="flex items-center gap-2.5 self-end md:self-center">
                        <button
                          onClick={() => {
                            setCaptionItem(item);
                            setCustomCaptionText(`${item.title}\n\nUnpack key insights from this episode.\n\n#repurpose #shorts #podcast`);
                          }}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-gray-300 text-xs font-medium transition-all"
                        >
                          <Edit3 className="w-3.5 h-3.5 text-indigo-400" />
                          <span>Customize Caption</span>
                        </button>

                        <button
                          onClick={() => handleRunWorkflow(selectedWorkflowForContent.id, item.id)}
                          disabled={isItemRunning}
                          className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
                        >
                          <Play className={`w-3.5 h-3.5 ${isItemRunning ? 'animate-spin' : ''}`} />
                          <span>{isItemRunning ? "Synthesizing..." : (isPublished ? "Republish" : "Repurpose Now")}</span>
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MULTI-PLATFORM CAPTION CUSTOMIZATION DRAWER                               */}
      {/* ========================================================================= */}
      {captionItem && selectedWorkflowForContent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-xl animate-fadeIn">
          <div className="surface-elevated rounded-3xl w-full max-w-xl p-6 space-y-5 shadow-2xl border border-white/10">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div>
                <h3 className="text-base font-bold font-display text-white">Custom Hook & Caption Editor</h3>
                <p className="text-xs text-gray-400 truncate max-w-md">{captionItem.title}</p>
              </div>
              <button onClick={() => setCaptionItem(null)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Platform Preview Selector */}
            <div className="flex items-center gap-2">
              {['tiktok', 'instagram', 'youtube', 'x', 'linkedin'].map(plat => (
                <button
                  key={plat}
                  onClick={() => setActiveCaptionPreviewPlatform(plat)}
                  className={`flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
                    activeCaptionPreviewPlatform === plat
                      ? 'bg-indigo-600/30 border-indigo-500 text-white'
                      : 'bg-white/[0.02] border-white/[0.06] text-gray-400 hover:text-white'
                  }`}
                >
                  {getPlatformIcon(plat)}
                  <span className="capitalize">{plat}</span>
                </button>
              ))}
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <label className="font-semibold text-gray-300">Hook Caption</label>
                <span className={`font-mono text-[11px] ${
                  customCaptionText.length > (PLATFORM_CHAR_LIMITS[activeCaptionPreviewPlatform] || 2200)
                    ? 'text-red-400 font-bold'
                    : 'text-gray-500'
                }`}>
                  {customCaptionText.length} / {PLATFORM_CHAR_LIMITS[activeCaptionPreviewPlatform] || 2200} chars
                </span>
              </div>
              <textarea
                rows={5}
                value={customCaptionText}
                onChange={e => setCustomCaptionText(e.target.value)}
                placeholder="Write hook and hashtags for this episode..."
                className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-white/[0.08] text-white text-xs focus:outline-none focus:border-indigo-500 font-sans"
              />
            </div>

            {/* Quick Hashtag Chips */}
            <div className="space-y-1.5">
              <span className="text-[11px] text-gray-400 font-semibold block">Quick-Add Hashtags</span>
              <div className="flex flex-wrap gap-1.5">
                {QUICK_TAG_SUGGESTIONS.map(tag => (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => {
                      if (!customCaptionText.includes(tag)) {
                        setCustomCaptionText(prev => `${prev} ${tag}`);
                      }
                    }}
                    className="px-2.5 py-1 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-[11px] font-mono text-gray-300 transition-all"
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/[0.08]">
              <button
                type="button"
                onClick={() => setCaptionItem(null)}
                className="px-4 py-2 rounded-xl bg-white/[0.04] text-gray-300 text-xs font-semibold hover:bg-white/[0.08]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => handleRunWorkflow(selectedWorkflowForContent.id, captionItem.id, customCaptionText)}
                className="px-5 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-md"
              >
                Save & Syndicate Episode
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 5-STEP CREATE WORKFLOW WIZARD MODAL                                       */}
      {/* ========================================================================= */}
      {isWizardOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/85 backdrop-blur-xl animate-fadeIn">
          <div className="surface-elevated rounded-3xl w-full max-w-3xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden border border-white/10">
            {/* Wizard Header & Progress Bar */}
            <div className="p-6 border-b border-white/[0.08] bg-[#080B11] space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                    <Plus className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold font-display text-white">Workflow Creator Studio</h3>
                    <p className="text-xs text-gray-400">
                      Step {currentStep} of 5 — {
                        currentStep === 1 ? 'Details & Execution Mode' :
                        currentStep === 2 ? 'Inbound Source Setup' :
                        currentStep === 3 ? 'Media Transformation' :
                        currentStep === 4 ? 'Destination Channels' :
                        'Rules & Drip Scheduling'
                      }
                    </p>
                  </div>
                </div>
                <button 
                  onClick={() => setIsWizardOpen(false)}
                  className="p-1 rounded-xl text-gray-400 hover:text-white hover:bg-white/[0.08]"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Step indicator pills */}
              <div className="grid grid-cols-5 gap-2">
                {[
                  { step: 1, label: 'Details' },
                  { step: 2, label: 'Source' },
                  { step: 3, label: 'Action' },
                  { step: 4, label: 'Destinations' },
                  { step: 5, label: 'Pacing' }
                ].map(s => (
                  <div key={s.step} className="space-y-1.5">
                    <div className={`h-1.5 rounded-full transition-all ${
                      currentStep >= s.step 
                        ? 'bg-gradient-to-r from-indigo-500 to-purple-500' 
                        : 'bg-white/[0.08]'
                    }`} />
                    <span className={`text-[10px] block font-mono font-semibold ${
                      currentStep === s.step ? 'text-indigo-400' : 'text-gray-500'
                    }`}>
                      0{s.step} {s.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Wizard Step Content Body */}
            <div className="p-6 overflow-y-auto flex-1 space-y-6 bg-[#0B0E17]">
              {/* STEP 1: Details & Mode */}
              {currentStep === 1 && (
                <div className="space-y-5 animate-fadeIn">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-300">Pipeline Name</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Founder Pod ➔ Vertical Shorts & Reels"
                      value={wfName}
                      onChange={e => setWfName(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-white/[0.08] text-white text-xs focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-300">Description</label>
                    <input
                      type="text"
                      placeholder="e.g. Automatically detect hook moments and publish vertical clips."
                      value={wfDesc}
                      onChange={e => setWfDesc(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-white/[0.08] text-white text-xs focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div className="space-y-2 pt-2">
                    <label className="text-xs font-semibold text-gray-300">Processing Mode</label>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div
                        onClick={() => setWfMode('AUTOMATIC')}
                        className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                          wfMode === 'AUTOMATIC'
                            ? 'bg-emerald-500/10 border-emerald-500/40 text-white'
                            : 'bg-white/[0.02] border-white/[0.06] text-gray-400 hover:text-white'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <Zap className="w-4 h-4 text-emerald-400" />
                          <span className="text-xs font-bold font-display text-emerald-400">⚡ Auto-Publish Mode</span>
                        </div>
                        <p className="text-[11px] text-gray-400 mt-1.5 leading-relaxed">
                          Zero-touch automation: new episodes detected in your RSS/channel are transformed and queued directly into your drip schedule.
                        </p>
                      </div>

                      <div
                        onClick={() => setWfMode('APPROVAL_REQUIRED')}
                        className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                          wfMode === 'APPROVAL_REQUIRED'
                            ? 'bg-amber-500/10 border-amber-500/40 text-white'
                            : 'bg-white/[0.02] border-white/[0.06] text-gray-400 hover:text-white'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <Lock className="w-4 h-4 text-amber-400" />
                          <span className="text-xs font-bold font-display text-amber-300">🛡️ Manual Review Mode</span>
                        </div>
                        <p className="text-[11px] text-gray-400 mt-1.5 leading-relaxed">
                          Safety first: new episodes wait in "View Content" for you to preview clips, polish captions, and publish on demand.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 2: Source Connection */}
              {currentStep === 2 && (
                <div className="space-y-5 animate-fadeIn">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-300">Select Inbound Channel</label>
                    <select
                      value={wfSourceId}
                      onChange={e => setWfSourceId(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-white/[0.08] text-white text-xs focus:outline-none focus:border-indigo-500 font-mono"
                    >
                      <option value="">Manual Upload (Trigger on manual file drop)</option>
                      {sources.map(src => (
                        <option key={src.id} value={src.id}>
                          {src.name} — {src.source_type}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-2">
                    <span className="text-xs font-bold font-display text-gray-300">Processing Scope</span>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-white">
                        <div className="text-xs font-bold">All Future Episodes</div>
                        <div className="text-[10px] text-gray-400 mt-0.5">Ingest new episodes automatically as they air.</div>
                      </div>
                      <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] text-gray-400">
                        <div className="text-xs font-bold">Snippets / Filtered</div>
                        <div className="text-[10px] text-gray-400 mt-0.5">Only episodes matching tag filters.</div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 3: Action & Media Styling */}
              {currentStep === 3 && (
                <div className="space-y-5 animate-fadeIn">
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-gray-300">Transformation Action</label>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      {[
                        { id: 'AI_CLIPS', label: 'AI Smart Clips', desc: 'Highlights & hooks detected via speech' },
                        { id: 'AUDIOGRAM', label: 'Audiogram (Soundwave)', desc: 'Dynamic waveform video from audio' },
                        { id: 'FULL_VIDEO', label: 'Full Video Re-frame', desc: 'Transcode full video to vertical 9:16' }
                      ].map(act => (
                        <div
                          key={act.id}
                          onClick={() => setActionType(act.id as any)}
                          className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                            actionType === act.id
                              ? 'bg-indigo-600/20 border-indigo-500 text-white font-semibold'
                              : 'bg-white/[0.02] border-white/[0.06] text-gray-400 hover:text-white'
                          }`}
                        >
                          <div className="text-xs font-bold font-display">{act.label}</div>
                          <div className="text-[11px] text-gray-400 mt-1">{act.desc}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
                    <div className="space-y-1.5">
                      <label className="text-[11px] text-gray-400">Aspect Ratio</label>
                      <select
                        value={aspectRatio}
                        onChange={e => setAspectRatio(e.target.value)}
                        className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/[0.08] text-white text-xs font-mono"
                      >
                        <option value="9:16">9:16 Vertical (Shorts, Reels, TikTok)</option>
                        <option value="1:1">1:1 Square (Instagram Feed, LinkedIn)</option>
                        <option value="16:9">16:9 Landscape (YouTube Desktop)</option>
                      </select>
                    </div>

                    {actionType === 'AUDIOGRAM' && (
                      <div className="space-y-1.5">
                        <label className="text-[11px] text-gray-400">Soundwave Style</label>
                        <select
                          value={waveformStyle}
                          onChange={e => setWaveformStyle(e.target.value as any)}
                          className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/[0.08] text-white text-xs font-mono"
                        >
                          <option value="BARS">Equalizer Bars</option>
                          <option value="LINE">Oscilloscope Line</option>
                          <option value="CIRCULAR">Circular Wave</option>
                          <option value="WAVE">Continuous Wave</option>
                        </select>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2 p-3 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                    <input
                      type="checkbox"
                      id="step_wm"
                      checked={stripWatermark}
                      onChange={e => setStripWatermark(e.target.checked)}
                      className="rounded bg-black border-gray-700 text-indigo-600 focus:ring-0"
                    />
                    <label htmlFor="step_wm" className="text-xs text-gray-300 cursor-pointer">
                      Automatically strip TikTok & Instagram watermarks cleanly via OCR
                    </label>
                  </div>
                </div>
              )}

              {/* STEP 4: Destinations & Accounts */}
              {currentStep === 4 && (
                <div className="space-y-5 animate-fadeIn">
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-gray-300">Select Publishing Destinations</label>
                    <div className="flex flex-wrap gap-2.5">
                      {['youtube', 'instagram', 'tiktok', 'linkedin', 'facebook', 'x'].map(plat => {
                        const isSelected = selectedPlatforms.includes(plat);
                        return (
                          <button
                            type="button"
                            key={plat}
                            onClick={() => {
                              setSelectedPlatforms(prev => 
                                isSelected ? prev.filter(p => p !== plat) : [...prev, plat]
                              );
                            }}
                            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all ${
                              isSelected
                                ? 'bg-indigo-600/30 text-white border-indigo-500'
                                : 'bg-white/[0.02] text-gray-400 border-white/[0.06] hover:text-white'
                            }`}
                          >
                            {getPlatformIcon(plat)}
                            <span className="capitalize">{plat}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="space-y-1.5 pt-2">
                    <label className="text-xs font-semibold text-gray-300">Default Caption Template</label>
                    <textarea
                      rows={3}
                      value={captionTemplate}
                      onChange={e => setCaptionTemplate(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-white/[0.08] text-white text-xs focus:outline-none focus:border-indigo-500 font-sans"
                    />
                    <span className="text-[10px] text-gray-500 font-mono">Variables: <code>{'{{title}}'}</code>, <code>{'{{description}}'}</code></span>
                  </div>
                </div>
              )}

              {/* STEP 5: Rules & Drip Schedule */}
              {currentStep === 5 && (
                <div className="space-y-5 animate-fadeIn">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-gray-300">Only Include If Tags Match</label>
                      <input
                        type="text"
                        placeholder="#shorts, #repurpose"
                        value={includeTags}
                        onChange={e => setIncludeTags(e.target.value)}
                        className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/[0.08] text-white text-xs font-mono"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-gray-300">Exclude If Tags Match</label>
                      <input
                        type="text"
                        placeholder="#sponsor, #ad"
                        value={excludeTags}
                        onChange={e => setExcludeTags(e.target.value)}
                        className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/[0.08] text-white text-xs font-mono"
                      />
                    </div>
                  </div>

                  <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          id="step_drip"
                          checked={dripEnabled}
                          onChange={e => setDripEnabled(e.target.checked)}
                          className="rounded bg-black border-gray-700 text-indigo-600 focus:ring-0"
                        />
                        <label htmlFor="step_drip" className="text-xs text-gray-300 font-semibold cursor-pointer">
                          Enable Intelligent Drip Pacing (avoid flooding followers)
                        </label>
                      </div>
                    </div>

                    {dripEnabled && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-white/[0.05]">
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-400">Post every:</span>
                          <input
                            type="number"
                            min={1}
                            max={48}
                            value={dripInterval}
                            onChange={e => setDripInterval(parseInt(e.target.value) || 4)}
                            className="w-16 px-2 py-1 rounded-lg bg-black/40 border border-white/[0.08] text-white text-xs text-center font-mono"
                          />
                          <span className="text-xs text-gray-400">hours</span>
                        </div>

                        <div className="flex items-center gap-2 text-xs text-gray-400 font-mono">
                          <span>Active hours:</span>
                          <span className="text-white font-sans font-medium">{activeHoursStart}:00 AM — {activeHoursEnd}:00 PM</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Wizard Navigation Footer */}
            <div className="p-4 border-t border-white/[0.08] bg-[#080B11] flex items-center justify-between">
              <button
                type="button"
                onClick={() => {
                  if (currentStep > 1) setCurrentStep((currentStep - 1) as any);
                  else setIsWizardOpen(false);
                }}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-gray-300 text-xs font-semibold transition-all"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>{currentStep === 1 ? 'Cancel' : 'Back'}</span>
              </button>

              {currentStep < 5 ? (
                <button
                  type="button"
                  onClick={() => {
                    if (currentStep === 1 && !wfName.trim()) {
                      alert("Please provide a workflow name.");
                      return;
                    }
                    setCurrentStep((currentStep + 1) as any);
                  }}
                  className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white text-xs font-semibold shadow-md transition-all"
                >
                  <span>Next Step</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleCreateWorkflow}
                  disabled={isSubmitting}
                  className="flex items-center gap-1.5 px-6 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white text-xs font-semibold shadow-lg shadow-emerald-500/20 transition-all disabled:opacity-50"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>{isSubmitting ? "Creating Pipeline..." : "Finish & Activate Workflow"}</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
