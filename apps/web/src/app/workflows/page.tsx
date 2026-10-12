"use client";

import React, { useState, useEffect } from 'react';
import { 
  GitBranch, 
  Play, 
  Save, 
  Plus, 
  Layers, 
  Sparkles, 
  Filter, 
  Clock, 
  Share2, 
  CheckCircle2, 
  Zap,
  ArrowRight,
  Split,
  Sliders,
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
  Radio,
  ExternalLink,
  ChevronRight
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

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<WorkflowItem[]>([]);
  const [sources, setSources] = useState<InboundSourceItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filterTab, setFilterTab] = useState<'all' | 'automatic' | 'approval'>('all');

  // Execution state
  const [runningWfId, setRunningWfId] = useState<string | null>(null);
  const [executionResult, setExecutionResult] = useState<any | null>(null);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
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
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['youtube', 'instagram']);
  const [captionTemplate, setCaptionTemplate] = useState('{{title}}\n\n{{description}}\n\n#repurpose #shorts');
  const [dripEnabled, setDripEnabled] = useState(true);
  const [dripInterval, setDripInterval] = useState(4);

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

  const handleToggleActive = async (wf: WorkflowItem) => {
    try {
      await api.updateWorkflow(wf.id, { active: !wf.active });
      setWorkflows(prev => prev.map(w => w.id === wf.id ? { ...w, active: !w.active } : w));
    } catch (err) {
      console.error("Failed to toggle workflow:", err);
    }
  };

  const handleRunWorkflow = async (workflowId: string) => {
    setRunningWfId(workflowId);
    setExecutionResult(null);
    try {
      const result = await api.runWorkflow(workflowId);
      setExecutionResult(result);
      await loadData();
    } catch (err: any) {
      setExecutionResult({
        status: "failed",
        error: err.message || "Workflow execution failed."
      });
    } finally {
      setRunningWfId(null);
    }
  };

  const handleDeleteWorkflow = async (id: string) => {
    if (!confirm("Are you sure you want to delete this workflow?")) return;
    try {
      await api.deleteWorkflow(id);
      setWorkflows(prev => prev.filter(w => w.id !== id));
    } catch (err) {
      console.error("Failed to delete workflow:", err);
    }
  };

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
          active_hours_start: 9,
          active_hours_end: 21
        }
      });

      setIsModalOpen(false);
      resetForm();
      await loadData();
    } catch (err) {
      console.error("Failed to create workflow:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setWfName('');
    setWfDesc('');
    setIncludeTags('#repurpose, #shorts');
    setExcludeTags('#sponsor, #ad');
    setActionType('AI_CLIPS');
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
    if (p.includes('youtube')) return <YoutubeIcon className="w-3.5 h-3.5 text-red-500" />;
    if (p.includes('instagram')) return <InstagramIcon className="w-3.5 h-3.5 text-pink-500" />;
    if (p.includes('tiktok')) return <TiktokIcon className="w-3.5 h-3.5 text-cyan-400" />;
    if (p.includes('linkedin')) return <LinkedinIcon className="w-3.5 h-3.5 text-blue-500" />;
    if (p.includes('facebook')) return <FacebookIcon className="w-3.5 h-3.5 text-blue-600" />;
    if (p.includes('x') || p.includes('twitter')) return <XIcon className="w-3.5 h-3.5 text-gray-300" />;
    return <Share2 className="w-3.5 h-3.5 text-gray-400" />;
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-16">
      {/* Top Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-indigo-500/20 to-purple-500/20 border border-indigo-500/30">
              <GitBranch className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Autonomous Repurpose Workflows</h1>
              <p className="text-xs text-gray-400 mt-0.5">
                Set and forget: auto-ingest podcasts, videos, or folders & publish native clips everywhere.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadData}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-[#161B26] hover:bg-[#1F2937] border border-[#1F2937] text-gray-300 text-xs font-medium transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-lg shadow-indigo-500/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Create Workflow</span>
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-[#111827] border border-[#1F2937]">
          <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Total Workflows</span>
          <div className="text-2xl font-bold text-white mt-1">{workflows.length}</div>
        </div>
        <div className="p-4 rounded-2xl bg-[#111827] border border-[#1F2937]">
          <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Active Pipelines</span>
          <div className="text-2xl font-bold text-emerald-400 mt-1">
            {workflows.filter(w => w.active).length}
          </div>
        </div>
        <div className="p-4 rounded-2xl bg-[#111827] border border-[#1F2937]">
          <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Total Executions</span>
          <div className="text-2xl font-bold text-indigo-400 mt-1">
            {workflows.reduce((acc, w) => acc + (w.execution_count || 0), 0)}
          </div>
        </div>
        <div className="p-4 rounded-2xl bg-[#111827] border border-[#1F2937]">
          <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">Connected Inbound Sources</span>
          <div className="text-2xl font-bold text-purple-400 mt-1">{sources.length}</div>
        </div>
      </div>

      {/* Execution Feedback Banner */}
      {executionResult && (
        <div className={`p-4 rounded-2xl border transition-all ${
          executionResult.status === 'succeeded' 
            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' 
            : executionResult.status === 'skipped'
            ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
            : 'bg-red-500/10 border-red-500/30 text-red-300'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {executionResult.status === 'succeeded' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              ) : (
                <AlertCircle className="w-4 h-4 text-amber-400" />
              )}
              <span className="text-xs font-semibold">
                {executionResult.status === 'succeeded' 
                  ? `Pipeline run succeeded! Created ${executionResult.publications_count || 0} scheduled publication(s).`
                  : executionResult.reason || executionResult.message || executionResult.error || "Workflow execution finished."}
              </span>
            </div>
            <button 
              onClick={() => setExecutionResult(null)}
              className="p-1 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center justify-between border-b border-[#1F2937] pb-3">
        <div className="flex items-center gap-2">
          {(['all', 'automatic', 'approval'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setFilterTab(tab)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                filterTab === tab
                  ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                  : 'text-gray-400 hover:text-white hover:bg-[#161B26]'
              }`}
            >
              {tab === 'all' && 'All Workflows'}
              {tab === 'automatic' && 'Auto-Publish Mode'}
              {tab === 'approval' && 'Approval Required'}
            </button>
          ))}
        </div>
      </div>

      {/* Workflows List */}
      {filteredWorkflows.length === 0 ? (
        <div className="text-center py-16 bg-[#111827] border border-[#1F2937] rounded-3xl p-8 space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto text-indigo-400">
            <GitBranch className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">No workflows configured yet</h3>
            <p className="text-xs text-gray-400 max-w-md mx-auto mt-1">
              Create your first workflow to link an inbound source (podcast, video, or folder) with automated clip generation and multi-platform drip publishing.
            </p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Create First Workflow</span>
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredWorkflows.map(wf => {
            const linkedSource = sources.find(s => s.id === wf.source_id);
            const isRunning = runningWfId === wf.id;

            return (
              <div 
                key={wf.id}
                className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 hover:border-gray-700 transition-all space-y-4 shadow-sm"
              >
                {/* Header row */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => handleToggleActive(wf)}
                      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                        wf.active ? 'bg-indigo-600' : 'bg-gray-700'
                      }`}
                    >
                      <span
                        className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                          wf.active ? 'translate-x-4' : 'translate-x-0'
                        }`}
                      />
                    </button>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-bold text-white tracking-tight">{wf.name}</h3>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                          wf.mode === 'AUTOMATIC'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                        }`}>
                          {wf.mode === 'AUTOMATIC' ? '⚡ Auto-Publish' : '🛡️ Approval Required'}
                        </span>
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5">{wf.description || "No description provided."}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleRunWorkflow(wf.id)}
                      disabled={isRunning || !wf.active}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/30 text-emerald-300 text-xs font-semibold transition-all disabled:opacity-40"
                    >
                      <Play className={`w-3.5 h-3.5 ${isRunning ? 'animate-spin' : ''}`} />
                      <span>{isRunning ? "Running..." : "Run Pipeline"}</span>
                    </button>
                    <button
                      onClick={() => handleDeleteWorkflow(wf.id)}
                      className="p-2 rounded-xl text-gray-400 hover:text-red-400 hover:bg-[#161B26] border border-transparent hover:border-[#1F2937] transition-all"
                      title="Delete workflow"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Pipeline Flow Visualizer */}
                <div className="p-3.5 rounded-xl bg-[#0B0F17] border border-[#1F2937]/80 flex flex-wrap items-center gap-3 text-xs">
                  {/* Source */}
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#161B26] border border-[#1F2937] text-gray-300">
                    <Zap className="w-3.5 h-3.5 text-amber-400" />
                    <span className="font-medium">
                      Source: {linkedSource ? linkedSource.name : (wf.trigger || 'Manual Upload')}
                    </span>
                  </div>

                  <ArrowRight className="w-3.5 h-3.5 text-gray-500 shrink-0" />

                  {/* Filter Rule */}
                  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#161B26] border border-[#1F2937] text-gray-300">
                    <Filter className="w-3.5 h-3.5 text-cyan-400" />
                    <span>
                      {wf.filters?.include_hashtags?.length 
                        ? `Tags: ${wf.filters.include_hashtags.join(', ')}`
                        : 'All Content'}
                    </span>
                  </div>

                  <ArrowRight className="w-3.5 h-3.5 text-gray-500 shrink-0" />

                  {/* Transformation Action */}
                  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#161B26] border border-[#1F2937] text-gray-300">
                    {wf.actions_config?.action_type === 'AUDIOGRAM' ? (
                      <Volume2 className="w-3.5 h-3.5 text-purple-400" />
                    ) : (
                      <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                    )}
                    <span>
                      {wf.actions_config?.action_type || 'AI_CLIPS'} ({wf.actions_config?.aspect_ratio || '9:16'})
                    </span>
                  </div>

                  <ArrowRight className="w-3.5 h-3.5 text-gray-500 shrink-0" />

                  {/* Destinations with Drip */}
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#161B26] border border-[#1F2937] text-gray-300">
                    <div className="flex items-center gap-1">
                      {wf.destinations?.map((d, i) => (
                        <span key={i} title={d.platform}>
                          {getPlatformIcon(d.platform)}
                        </span>
                      ))}
                    </div>
                    {wf.drip_config?.drip_enabled && (
                      <span className="text-[10px] text-emerald-400 font-semibold bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                        Drip: Every {wf.drip_config.interval_hours || 4}h
                      </span>
                    )}
                  </div>
                </div>

                {/* Footer status */}
                <div className="flex items-center justify-between text-[11px] text-gray-400 pt-1">
                  <div className="flex items-center gap-3">
                    <span>Executions: <strong className="text-white">{wf.execution_count || 0}</strong></span>
                    <span>Last run: <strong className="text-gray-300">{wf.last_run_at ? new Date(wf.last_run_at).toLocaleString() : 'Never'}</strong></span>
                  </div>
                  <div>
                    {wf.actions_config?.strip_watermark && (
                      <span className="text-emerald-400">✓ Watermark Auto-Strip</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Workflow Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[#111827] border border-[#1F2937] rounded-3xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#1F2937] pb-4">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-indigo-500/20 border border-indigo-500/30 text-indigo-400">
                  <Plus className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Create Automated Workflow</h3>
                  <p className="text-xs text-gray-400">Connect source content to multi-channel syndication.</p>
                </div>
              </div>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="p-1 rounded-xl text-gray-400 hover:text-white hover:bg-[#161B26]"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateWorkflow} className="space-y-5">
              {/* Name & Mode */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300">Workflow Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Podcast to Shorts & Reels"
                    value={wfName}
                    onChange={e => setWfName(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-[#161B26] border border-[#1F2937] text-white text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300">Execution Mode</label>
                  <select
                    value={wfMode}
                    onChange={e => setWfMode(e.target.value as any)}
                    className="w-full px-3 py-2 rounded-xl bg-[#161B26] border border-[#1F2937] text-white text-xs focus:outline-none focus:border-indigo-500"
                  >
                    <option value="AUTOMATIC">⚡ Auto-Publish (Hands-Free)</option>
                    <option value="APPROVAL_REQUIRED">🛡️ Approval Required (Review First)</option>
                  </select>
                </div>
              </div>

              {/* Inbound Source Selection */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-300">Inbound Source Trigger</label>
                <select
                  value={wfSourceId}
                  onChange={e => setWfSourceId(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#161B26] border border-[#1F2937] text-white text-xs focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Manual Upload (Trigger on manual file upload)</option>
                  {sources.map(src => (
                    <option key={src.id} value={src.id}>
                      {src.name} ({src.source_type})
                    </option>
                  ))}
                </select>
              </div>

              {/* Filters */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300">Only Include If Tags Match</label>
                  <input
                    type="text"
                    placeholder="e.g. #repurpose, #shorts (comma separated)"
                    value={includeTags}
                    onChange={e => setIncludeTags(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-[#161B26] border border-[#1F2937] text-white text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300">Exclude If Tags Match</label>
                  <input
                    type="text"
                    placeholder="e.g. #sponsor, #ad"
                    value={excludeTags}
                    onChange={e => setExcludeTags(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-[#161B26] border border-[#1F2937] text-white text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              {/* Transformation Action */}
              <div className="p-4 rounded-2xl bg-[#161B26] border border-[#1F2937] space-y-3">
                <span className="text-xs font-bold text-gray-300 uppercase tracking-wider block">
                  Media Transformation
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {[
                    { id: 'AI_CLIPS', label: 'AI Smart Clips', desc: 'Auto-detect highlights & hook clips' },
                    { id: 'AUDIOGRAM', label: 'Audiogram (Soundwave)', desc: 'Convert podcast audio to video' },
                    { id: 'FULL_VIDEO', label: 'Full Video Re-frame', desc: 'Transcode to 9:16 vertical' }
                  ].map(act => (
                    <div
                      key={act.id}
                      onClick={() => setActionType(act.id as any)}
                      className={`p-3 rounded-xl border cursor-pointer transition-all ${
                        actionType === act.id
                          ? 'bg-indigo-600/20 border-indigo-500 text-white'
                          : 'bg-[#111827] border-[#1F2937] text-gray-400 hover:text-white'
                      }`}
                    >
                      <div className="text-xs font-bold">{act.label}</div>
                      <div className="text-[11px] text-gray-400 mt-0.5">{act.desc}</div>
                    </div>
                  ))}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                  <div className="space-y-1">
                    <label className="text-[11px] text-gray-400">Target Aspect Ratio</label>
                    <select
                      value={aspectRatio}
                      onChange={e => setAspectRatio(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-xl bg-[#111827] border border-[#1F2937] text-white text-xs"
                    >
                      <option value="9:16">9:16 Vertical (Shorts/Reels/TikTok)</option>
                      <option value="1:1">1:1 Square (LinkedIn/Instagram Feed)</option>
                      <option value="16:9">16:9 Landscape (YouTube)</option>
                    </select>
                  </div>
                  {actionType === 'AUDIOGRAM' && (
                    <div className="space-y-1">
                      <label className="text-[11px] text-gray-400">Soundwave Style</label>
                      <select
                        value={waveformStyle}
                        onChange={e => setWaveformStyle(e.target.value as any)}
                        className="w-full px-3 py-1.5 rounded-xl bg-[#111827] border border-[#1F2937] text-white text-xs"
                      >
                        <option value="BARS">Equalizer Bars</option>
                        <option value="LINE">Oscilloscope Line</option>
                        <option value="CIRCULAR">Circular Wave</option>
                        <option value="WAVE">Continuous Wave</option>
                      </select>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 pt-2">
                  <input
                    type="checkbox"
                    id="strip_wm"
                    checked={stripWatermark}
                    onChange={e => setStripWatermark(e.target.checked)}
                    className="rounded bg-[#111827] border-gray-700 text-indigo-600 focus:ring-0"
                  />
                  <label htmlFor="strip_wm" className="text-xs text-gray-300 cursor-pointer">
                    Automatically strip platform watermarks (TikTok / Instagram)
                  </label>
                </div>
              </div>

              {/* Destinations & Drip Schedule */}
              <div className="p-4 rounded-2xl bg-[#161B26] border border-[#1F2937] space-y-3">
                <span className="text-xs font-bold text-gray-300 uppercase tracking-wider block">
                  Outbound Destinations & Drip Pacing
                </span>

                <div className="flex flex-wrap gap-2">
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
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                          isSelected
                            ? 'bg-indigo-600 text-white border-indigo-500'
                            : 'bg-[#111827] text-gray-400 border-[#1F2937] hover:text-white'
                        }`}
                      >
                        {getPlatformIcon(plat)}
                        <span className="capitalize">{plat}</span>
                      </button>
                    );
                  })}
                </div>

                <div className="space-y-1.5 pt-2">
                  <label className="text-xs font-semibold text-gray-300">Caption Template</label>
                  <textarea
                    rows={2}
                    value={captionTemplate}
                    onChange={e => setCaptionTemplate(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-[#111827] border border-[#1F2937] text-white text-xs focus:outline-none focus:border-indigo-500"
                  />
                  <span className="text-[10px] text-gray-400">Available variables: <code>{'{{title}}'}</code>, <code>{'{{description}}'}</code></span>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-[#1F2937]">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="drip_en"
                      checked={dripEnabled}
                      onChange={e => setDripEnabled(e.target.checked)}
                      className="rounded bg-[#111827] border-gray-700 text-indigo-600 focus:ring-0"
                    />
                    <label htmlFor="drip_en" className="text-xs text-gray-300 cursor-pointer">
                      Enable Drip Pacing (avoid posting bursts)
                    </label>
                  </div>
                  {dripEnabled && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs text-gray-400">Every</span>
                      <input
                        type="number"
                        min={1}
                        max={48}
                        value={dripInterval}
                        onChange={e => setDripInterval(parseInt(e.target.value) || 4)}
                        className="w-14 px-2 py-1 rounded-lg bg-[#111827] border border-[#1F2937] text-white text-xs text-center"
                      />
                      <span className="text-xs text-gray-400">hours</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-[#161B26] hover:bg-[#1F2937] text-gray-300 text-xs font-semibold transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-lg shadow-indigo-500/20 transition-all disabled:opacity-50"
                >
                  {isSubmitting ? "Creating..." : "Save Workflow"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
