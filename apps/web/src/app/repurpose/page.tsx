"use client";

import React, { useState, useEffect, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { 
  Sparkles, 
  Play, 
  Copy, 
  CheckCheck, 
  RefreshCw,
  Info,
  Layers,
  FileText,
  Clock,
  Send,
  RotateCcw,
  Tag,
  ChevronDown,
  ChevronUp,
  Quote,
  CheckCircle2,
  Film,
  Download,
  Trash2,
  Sliders,
  Scissors,
  ExternalLink,
  Type,
  Subtitles,
  Sparkle,
  UploadCloud,
  Globe,
  AlertTriangle,
  X,
  Lock,
  Share2
} from 'lucide-react';
import { YoutubeIcon, InstagramIcon, TiktokIcon, LinkedinIcon, XIcon, FacebookIcon } from '@/components/ui/SocialIcons';
import { 
  ContentItem, 
  ContentVariant, 
  Transcript, 
  ContentBrief, 
  GeneratedContent, 
  ClipItem, 
  CaptionCue, 
  ClipCaptionsData,
  PlatformConnectionItem,
  PublicationItem
} from '@/types';
import { api } from '@/lib/api';

function RepurposeContent() {
  const searchParams = useSearchParams();
  const contentId = searchParams.get('id');

  const [content, setContent] = useState<ContentItem | null>(null);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [brief, setBrief] = useState<ContentBrief | null>(null);
  const [generatedList, setGeneratedList] = useState<GeneratedContent[]>([]);
  const [clipsList, setClipsList] = useState<ClipItem[]>([]);
  const [connections, setConnections] = useState<PlatformConnectionItem[]>([]);
  const [publications, setPublications] = useState<PublicationItem[]>([]);
  
  const [mainStudioTab, setMainStudioTab] = useState<'copy' | 'clips'>('copy');
  const [selectedFormat, setSelectedFormat] = useState('9:16');
  const [activeOutputTab, setActiveOutputTab] = useState('linkedin');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isDiscoveringClips, setIsDiscoveringClips] = useState(false);
  const [generatingClipId, setGeneratingClipId] = useState<string | null>(null);
  const [isRenderingCaptions, setIsRenderingCaptions] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);
  const [isTranscriptExpanded, setIsTranscriptExpanded] = useState(false);

  // Selected Clip Candidate State
  const [selectedClip, setSelectedClip] = useState<ClipItem | null>(null);
  const [editedStartTime, setEditedStartTime] = useState<number>(0);
  const [editedEndTime, setEditedEndTime] = useState<number>(30);
  const [selectedClipRatio, setSelectedClipRatio] = useState<string>('9:16');
  
  // Phase 6 Captions & Subtitles State
  const [captionsData, setCaptionsData] = useState<ClipCaptionsData | null>(null);
  const [selectedCaptionStyle, setSelectedCaptionStyle] = useState<string>('BOLD_PUNCH');
  const [captionsEnabled, setCaptionsEnabled] = useState<boolean>(true);
  const [highlightKeywordsInput, setHighlightKeywordsInput] = useState<string>('');
  const [activeCaptionCue, setActiveCaptionCue] = useState<CaptionCue | null>(null);
  const [currentPlaybackTime, setCurrentPlaybackTime] = useState<number>(0);
  
  // Phase 7 & 8 Multi-Platform Publishing Flow State
  const [isPublishModalOpen, setIsPublishModalOpen] = useState(false);
  const [targetPublishClip, setTargetPublishClip] = useState<ClipItem | null>(null);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['youtube']);
  const [activeModalPlatform, setActiveModalPlatform] = useState<string>('youtube');
  const [platformMetaMap, setPlatformMetaMap] = useState<Record<string, { connectionId: string; title: string; description: string; tags: string; privacy: 'PRIVATE' | 'UNLISTED' | 'PUBLIC' }>>({});
  const [isPublishing, setIsPublishing] = useState<boolean>(false);
  const [publishFeedback, setPublishFeedback] = useState<string | null>(null);
  const [retryingPubId, setRetryingPubId] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (contentId) {
      loadAllData(contentId);
    }
  }, [contentId]);

  const loadAllData = async (id: string) => {
    try {
      const c = await api.getContent(id);
      setContent(c);

      // Load Transcript
      try {
        const t = await api.getTranscript(id);
        setTranscript(t);
      } catch {}

      // Load Brief
      try {
        const b = await api.getContentBrief(id);
        setBrief(b);
      } catch {}

      // Load Generated Outputs
      try {
        const g = await api.getGeneratedContent(id);
        setGeneratedList(g);
      } catch {}

      // Load Clips
      try {
        const cl = await api.getContentClips(id);
        setClipsList(cl.items);
        if (cl.items.length > 0 && !selectedClip) {
          handleSelectClip(cl.items[0]);
        }
      } catch {}

      // Load Connections
      try {
        const conns = await api.getPlatformConnections();
        setConnections(conns.items || []);
      } catch {}

      // Load Publications
      try {
        const pubs = await api.getPublications(id);
        setPublications(pubs.items || []);
      } catch {}

    } catch (e) {
      console.warn("Failed to load content data:", e);
    }
  };

  const loadPublications = async (id: string) => {
    try {
      const pubs = await api.getPublications(id);
      setPublications(pubs.items || []);
    } catch {}
  };

  const loadClipCaptions = async (clipId: string) => {
    try {
      const cap = await api.getClipCaptions(clipId);
      setCaptionsData(cap);
      setSelectedCaptionStyle(cap.caption_style || 'BOLD_PUNCH');
      setCaptionsEnabled(cap.caption_enabled);
      setHighlightKeywordsInput((cap.highlight_keywords || []).join(', '));
    } catch (e) {
      console.warn("Failed to load clip captions:", e);
    }
  };

  const formats = [
    { id: '16:9', label: 'Landscape (16:9)', variantType: 'LANDSCAPE_16_9' },
    { id: '9:16', label: 'Vertical (9:16)', variantType: 'VERTICAL_9_16' },
    { id: '1:1', label: 'Square (1:1)', variantType: 'SQUARE_1_1' },
    { id: '4:5', label: 'Portrait (4:5)', variantType: 'PORTRAIT_4_5' },
  ];

  const matchedVariant = content?.variants?.find(v => v.variant_type === formats.find(f => f.id === selectedFormat)?.variantType);
  const primaryAsset = content?.assets && content.assets[0];
  const activeMediaUrl = matchedVariant
    ? api.getVariantUrl(content!.id, matchedVariant.id)
    : (primaryAsset ? api.getAssetUrl(content!.id, primaryAsset.id) : null);

  const activeGenItem = generatedList.find(g => g.platform.toLowerCase() === activeOutputTab.toLowerCase());
  const activePayload = activeGenItem?.payload || {};

  const handleGenerateAll = async () => {
    if (!contentId) return;
    setIsGenerating(true);
    setActionFeedback(null);
    try {
      await api.triggerAiGeneration(contentId, ["LINKEDIN", "INSTAGRAM", "X", "YOUTUBE"]);
      setActionFeedback("AI Content Intelligence generation queued! Polling for synthesized outputs...");
      setTimeout(() => loadAllData(contentId), 2000);
    } catch (e: any) {
      setActionFeedback(`Generation failed: ${e.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDiscoverClips = async () => {
    if (!contentId) return;
    setIsDiscoveringClips(true);
    setActionFeedback(null);
    try {
      await api.discoverClips(contentId, { force_refresh: true });
      setActionFeedback("AI moment discovery in progress! Extracting viral hooks...");
      setTimeout(async () => {
        const res = await api.getContentClips(contentId);
        setClipsList(res.items);
        if (res.items.length > 0) {
          handleSelectClip(res.items[0]);
        }
        setIsDiscoveringClips(false);
      }, 3000);
    } catch (e: any) {
      setActionFeedback(`Clip discovery failed: ${e.message}`);
      setIsDiscoveringClips(false);
    }
  };

  const handleSelectClip = (clip: ClipItem) => {
    setSelectedClip(clip);
    setEditedStartTime(clip.start_time);
    setEditedEndTime(clip.end_time);
    loadClipCaptions(clip.id);

    // Jump preview video to clip start time
    if (videoRef.current) {
      videoRef.current.currentTime = clip.start_time;
      videoRef.current.play().catch(() => {});
    }
  };

  const handleTimeUpdate = () => {
    if (!videoRef.current) return;
    const t = videoRef.current.currentTime;
    setCurrentPlaybackTime(t);

    if (mainStudioTab === 'clips' && selectedClip && captionsEnabled && captionsData?.cues) {
      const relTime = t - selectedClip.start_time;
      const matchedCue = captionsData.cues.find(
        (c) => relTime >= c.start_time && relTime <= c.end_time
      );
      setActiveCaptionCue(matchedCue || null);
    } else {
      setActiveCaptionCue(null);
    }
  };

  const handleUpdateClipTiming = async () => {
    if (!selectedClip) return;
    try {
      const updated = await api.updateClip(selectedClip.id, {
        start_time: editedStartTime,
        end_time: editedEndTime
      });
      setSelectedClip(updated);
      setClipsList(prev => prev.map(c => c.id === updated.id ? updated : c));
      setActionFeedback("Clip interval updated.");
      loadClipCaptions(updated.id);
    } catch (e: any) {
      setActionFeedback(`Failed to update clip: ${e.message}`);
    }
  };

  const handleGenerateSingleClip = async (clipId: string, burnCaptions: boolean = false) => {
    setGeneratingClipId(clipId);
    setActionFeedback(null);
    try {
      const keywords = highlightKeywordsInput.split(',').map(k => k.trim()).filter(Boolean);
      await api.generateClip(clipId, { 
        aspect_ratios: [selectedClipRatio], 
        include_thumbnail: true,
        burn_captions: burnCaptions,
        caption_style: selectedCaptionStyle,
        highlight_keywords: keywords
      });
      setActionFeedback(`Clip transcoding enqueued (${selectedClipRatio}${burnCaptions ? ' with Burned Captions' : ''})!`);
      setTimeout(async () => {
        if (contentId) await loadAllData(contentId);
        setGeneratingClipId(null);
      }, 3500);
    } catch (e: any) {
      setActionFeedback(`Clip generation failed: ${e.message}`);
      setGeneratingClipId(null);
    }
  };

  const handleUpdateCaptionSettings = async () => {
    if (!selectedClip) return;
    const keywords = highlightKeywordsInput.split(',').map(k => k.trim()).filter(Boolean);
    try {
      const updated = await api.updateClipCaptions(selectedClip.id, {
        caption_style: selectedCaptionStyle,
        caption_enabled: captionsEnabled,
        highlight_keywords: keywords
      });
      setCaptionsData(updated);
      setActionFeedback("Caption styling preferences saved.");
    } catch (e: any) {
      setActionFeedback(`Failed to update caption settings: ${e.message}`);
    }
  };

  const handleRenderCaptions = async () => {
    if (!selectedClip) return;
    setIsRenderingCaptions(true);
    setActionFeedback(null);
    const keywords = highlightKeywordsInput.split(',').map(k => k.trim()).filter(Boolean);
    try {
      await api.renderClipCaptions(selectedClip.id, [selectedClipRatio], selectedCaptionStyle, keywords);
      setActionFeedback(`Caption burning job queued (${selectedCaptionStyle})! Rendering styled overlay cards...`);
      setTimeout(async () => {
        if (contentId) await loadAllData(contentId);
        setIsRenderingCaptions(false);
      }, 3500);
    } catch (e: any) {
      setActionFeedback(`Caption render failed: ${e.message}`);
      setIsRenderingCaptions(false);
    }
  };

  const handleDeleteClip = async (clipId: string) => {
    try {
      await api.deleteClip(clipId);
      setClipsList(prev => prev.filter(c => c.id !== clipId));
      if (selectedClip?.id === clipId) setSelectedClip(null);
      setActionFeedback("Clip deleted.");
    } catch (e: any) {
      setActionFeedback(`Delete failed: ${e.message}`);
    }
  };

  const handleRegeneratePlatform = async (platform: string) => {
    if (!contentId) return;
    setIsRegenerating(true);
    try {
      await api.regeneratePlatform(contentId, platform);
      await loadAllData(contentId);
      setActionFeedback(`Regenerated latest ${platform} output.`);
    } catch (e: any) {
      setActionFeedback(`Regeneration error: ${e.message}`);
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleOpenPublishModal = (clip?: ClipItem) => {
    const target = clip || selectedClip;
    setTargetPublishClip(target || null);
    
    const initialPlatforms = ['youtube', 'instagram', 'linkedin', 'x', 'facebook', 'tiktok'];
    const newMap: Record<string, { connectionId: string; title: string; description: string; tags: string; privacy: 'PRIVATE' | 'UNLISTED' | 'PUBLIC' }> = {};

    initialPlatforms.forEach(p => {
      const conn = connections.find(c => c.platform.toLowerCase() === p && c.status === 'CONNECTED');
      const aiGen = generatedList.find(g => g.platform.toLowerCase() === p);
      let payload: any = {};
      if (aiGen && aiGen.payload) {
        payload = typeof aiGen.payload === 'string' ? JSON.parse(aiGen.payload) : aiGen.payload;
      }

      const defaultTitle = target?.title || content?.title || "Reflow Video";
      const defaultDesc = payload.caption || payload.hook || target?.hook || brief?.summary || "Created with Reflow.";
      const defaultTags = (payload.hashtags && payload.hashtags.length > 0) 
        ? payload.hashtags.join(', ')
        : (brief?.topics?.join(', ') || 'reflow, ai');

      newMap[p] = {
        connectionId: conn ? conn.id : '',
        title: defaultTitle,
        description: defaultDesc,
        tags: defaultTags,
        privacy: 'PRIVATE'
      };
    });

    setPlatformMetaMap(newMap);
    setSelectedPlatforms(['youtube']);
    setActiveModalPlatform('youtube');
    setPublishFeedback(null);
    setIsPublishModalOpen(true);
  };

  const handleConfirmPublish = async () => {
    if (!contentId || selectedPlatforms.length === 0) return;

    // Validate that each selected platform has a connected account
    const destinations = [];
    for (const p of selectedPlatforms) {
      const meta = platformMetaMap[p];
      if (!meta || !meta.connectionId) {
        setPublishFeedback(`No connected account selected for ${p.toUpperCase()}. Connect in Connections page or deselect.`);
        return;
      }
      if (!meta.title.trim() && p === 'youtube') {
        setPublishFeedback(`Title is required for YouTube.`);
        return;
      }
      destinations.push({
        platform_connection_id: meta.connectionId,
        title: meta.title.trim(),
        description: meta.description.trim(),
        privacy: meta.privacy,
        tags: meta.tags.split(',').map(t => t.trim()).filter(Boolean)
      });
    }

    setIsPublishing(true);
    setPublishFeedback(null);

    // Pick target variant
    let variantId = undefined;
    if (targetPublishClip) {
      const varItem = targetPublishClip.variants?.find(v => v.has_captions && v.variant_type.includes("9_16")) 
        || targetPublishClip.variants?.find(v => v.variant_type.includes("9_16"))
        || targetPublishClip.variants?.[0];
      variantId = varItem?.id;
    } else if (matchedVariant) {
      variantId = matchedVariant.id;
    }

    try {
      const res = await api.createBatchPublications({
        content_id: contentId,
        variant_id: variantId,
        destinations: destinations
      });

      setActionFeedback(`Batch publishing queued across ${res.queued_count} platform destination(s)!`);
      setIsPublishModalOpen(false);
      await loadPublications(contentId);

      // Start periodic status polling
      const pollInterval = setInterval(async () => {
        if (contentId) {
          const pRes = await api.getPublications(contentId);
          setPublications(pRes.items || []);
          const stillActive = pRes.items.some(p => p.status === 'QUEUED' || p.status === 'UPLOADING' || p.status === 'PUBLISHING');
          if (!stillActive) {
            clearInterval(pollInterval);
          }
        }
      }, 3000);

    } catch (err: any) {
      setPublishFeedback(`Batch publishing error: ${err.message}`);
    } finally {
      setIsPublishing(false);
    }
  };

  const handleRetryPublication = async (pubId: string) => {
    try {
      setRetryingPubId(pubId);
      await api.retryPublication(pubId);
      setActionFeedback("Retrying publication...");
      if (contentId) await loadPublications(contentId);
    } catch (err: any) {
      setActionFeedback(`Retry failed: ${err.message}`);
    } finally {
      setRetryingPubId(null);
    }
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // Caption Styling Visualizer for Live Preview Overlay
  const getCaptionOverlayClass = (style: string) => {
    switch (style) {
      case 'BOLD_PUNCH':
        return 'bg-black/85 border border-yellow-400 text-yellow-300 font-black tracking-wide text-sm sm:text-base px-4 py-2 rounded-xl shadow-2xl';
      case 'CLEAN_SUBTITLE':
        return 'bg-slate-900/85 border border-indigo-500/50 text-white font-bold text-xs sm:text-sm px-4 py-1.5 rounded-lg shadow-lg';
      case 'KINETIC_HIGHLIGHT':
        return 'bg-purple-950/90 border border-cyan-400 text-white font-black text-sm sm:text-base px-4 py-2 rounded-xl shadow-2xl';
      case 'MINIMAL_WHITE':
        return 'bg-black/60 border border-white/20 text-gray-100 font-medium text-xs sm:text-sm px-3 py-1 rounded shadow';
      default:
        return 'bg-black/80 text-yellow-400 font-bold px-3 py-1.5 rounded-lg';
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Repurpose Studio</h1>
            <span className="text-xs bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded-full border border-indigo-500/20 font-mono">
              v1.0 Ready
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            {content ? `Reflowing: "${content.title}"` : 'Select an asset from the Content Library to repurpose'}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Main Studio Mode Toggle */}
          <div className="bg-[#111827] border border-[#1F2937] p-1 rounded-xl flex items-center gap-1">
            <button
              onClick={() => setMainStudioTab('copy')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                mainStudioTab === 'copy' ? 'bg-indigo-600 text-white shadow' : 'text-gray-400 hover:text-white'
              }`}
            >
              <Type className="w-3.5 h-3.5" />
              <span>Native Copy</span>
            </button>
            <button
              onClick={() => setMainStudioTab('clips')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                mainStudioTab === 'clips' ? 'bg-purple-600 text-white shadow' : 'text-gray-400 hover:text-white'
              }`}
            >
              <Film className="w-3.5 h-3.5" />
              <span>Clips & Captions</span>
            </button>
          </div>

          {/* Publish Action Button */}
          <button
            onClick={() => handleOpenPublishModal()}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold shadow-md shadow-red-600/20 transition-all"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Publish to Social</span>
          </button>

          {mainStudioTab === 'copy' ? (
            <button
              onClick={handleGenerateAll}
              disabled={isGenerating || !contentId}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-md shadow-indigo-500/20 transition-all disabled:opacity-50"
            >
              <Sparkles className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin' : ''}`} />
              <span>{isGenerating ? "Synthesizing AI Intelligence..." : "Synthesize AI Intelligence"}</span>
            </button>
          ) : (
            <button
              onClick={handleDiscoverClips}
              disabled={isDiscoveringClips || !contentId}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold shadow-md shadow-purple-500/20 transition-all disabled:opacity-50"
            >
              <Scissors className={`w-3.5 h-3.5 ${isDiscoveringClips ? 'animate-spin' : ''}`} />
              <span>{isDiscoveringClips ? "Discovering Moments..." : "Discover AI Clips"}</span>
            </button>
          )}
        </div>
      </div>

      {/* Feedback Banner */}
      {actionFeedback && (
        <div className="p-3 bg-indigo-500/10 border border-indigo-500/30 rounded-xl flex items-center justify-between text-xs text-indigo-300 animate-fadeIn">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-indigo-400" />
            <span>{actionFeedback}</span>
          </div>
          <button onClick={() => setActionFeedback(null)} className="text-gray-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Main Studio Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column (5 cols): Media Player, Live Preview, & Timing Controls */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" />
                <span className="text-xs font-bold text-white uppercase tracking-wider">
                  {mainStudioTab === 'clips' ? 'Clip Timing & Live Captions' : 'Original Media Canvas'}
                </span>
              </div>
              <span className="text-xs text-gray-500 font-mono">
                {mainStudioTab === 'clips' ? selectedClipRatio : selectedFormat}
              </span>
            </div>

            {/* Video Container with Synchronized Live Caption Overlay */}
            <div className="relative aspect-video rounded-xl bg-black overflow-hidden border border-[#1F2937] flex items-center justify-center group shadow-inner">
              {activeMediaUrl ? (
                <video
                  ref={videoRef}
                  src={activeMediaUrl}
                  controls
                  onTimeUpdate={handleTimeUpdate}
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="text-center p-6 space-y-2">
                  <Play className="w-8 h-8 text-gray-600 mx-auto" />
                  <p className="text-xs text-gray-500">No media available to preview</p>
                </div>
              )}

              {/* Synchronized Real-time Subtitle Overlay on Video */}
              {mainStudioTab === 'clips' && activeCaptionCue && (
                <div className="absolute inset-x-0 bottom-12 flex justify-center px-4 pointer-events-none z-20 animate-fadeIn">
                  <div className={getCaptionOverlayClass(selectedCaptionStyle)}>
                    <span>{activeCaptionCue.text}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Mode Specific Controls */}
            {mainStudioTab === 'clips' && selectedClip && (
              <div className="space-y-4 pt-1">
                {/* 1. Timing Fine-Tuning Slider Controls */}
                <div className="bg-[#161B26] border border-[#1F2937] rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between text-xs font-bold text-white">
                    <span className="flex items-center gap-1.5">
                      <Sliders className="w-3.5 h-3.5 text-purple-400" />
                      <span>Timeline Fine-Tuning</span>
                    </span>
                    <span className="font-mono text-indigo-400">
                      Duration: {(editedEndTime - editedStartTime).toFixed(1)}s
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <label className="text-[10px] text-gray-400 block mb-1 font-mono">Start (sec)</label>
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        value={editedStartTime}
                        onChange={(e) => setEditedStartTime(parseFloat(e.target.value) || 0)}
                        className="w-full bg-[#111827] border border-[#1F2937] rounded-lg px-2.5 py-1 text-white font-mono"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-gray-400 block mb-1 font-mono">End (sec)</label>
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        value={editedEndTime}
                        onChange={(e) => setEditedEndTime(parseFloat(e.target.value) || 0)}
                        className="w-full bg-[#111827] border border-[#1F2937] rounded-lg px-2.5 py-1 text-white font-mono"
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <button
                      onClick={handleUpdateClipTiming}
                      className="px-3 py-1 rounded-lg bg-gray-800 hover:bg-gray-700 text-white text-xs font-semibold transition"
                    >
                      Save Timing
                    </button>

                    <div className="flex items-center gap-2">
                      <select
                        value={selectedClipRatio}
                        onChange={(e) => setSelectedClipRatio(e.target.value)}
                        className="bg-[#111827] border border-[#1F2937] text-gray-300 text-xs rounded-lg px-2 py-1.5 font-mono focus:outline-none"
                      >
                        <option value="9:16">9:16 (Vertical Reel)</option>
                        <option value="1:1">1:1 (Square)</option>
                        <option value="4:5">4:5 (Portrait)</option>
                        <option value="16:9">16:9 (Landscape)</option>
                      </select>

                      <button
                        onClick={() => handleGenerateSingleClip(selectedClip.id, false)}
                        disabled={generatingClipId === selectedClip.id}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all disabled:opacity-50"
                      >
                        {generatingClipId === selectedClip.id ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Film className="w-3.5 h-3.5" />}
                        <span>Clean Clip</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* 2. Captions & Subtitles Styling Studio */}
                <div className="bg-[#161B26] border border-[#1F2937] rounded-xl p-4 space-y-3.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-white">
                      <Subtitles className="w-3.5 h-3.5 text-yellow-400" />
                      <span>Captions & Subtitle Styling</span>
                    </div>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <span className="text-[11px] text-gray-400">Live Overlay</span>
                      <input
                        type="checkbox"
                        checked={captionsEnabled}
                        onChange={(e) => setCaptionsEnabled(e.target.checked)}
                        className="rounded border-gray-700 bg-gray-900 text-yellow-400 focus:ring-0"
                      />
                    </label>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { id: 'BOLD_PUNCH', name: 'Bold Punch', desc: 'Viral Yellow/Dark', color: 'text-yellow-400 border-yellow-500/40 bg-yellow-500/10' },
                      { id: 'CLEAN_SUBTITLE', name: 'Clean Subtitle', desc: 'Minimal Slate', color: 'text-indigo-300 border-indigo-500/40 bg-indigo-500/10' },
                      { id: 'KINETIC_HIGHLIGHT', name: 'Kinetic', desc: 'Neon Cyan Highlights', color: 'text-cyan-300 border-cyan-500/40 bg-cyan-500/10' },
                      { id: 'MINIMAL_WHITE', name: 'Minimal White', desc: 'Translucent Subtitle', color: 'text-gray-300 border-gray-600 bg-gray-800/40' },
                    ].map((style) => (
                      <button
                        key={style.id}
                        onClick={() => setSelectedCaptionStyle(style.id)}
                        className={`p-2.5 rounded-lg border text-left transition-all ${
                          selectedCaptionStyle === style.id
                            ? `${style.color} ring-1 ring-white/20 shadow-md`
                            : 'bg-[#111827] border-[#1F2937] text-gray-400 hover:text-white'
                        }`}
                      >
                        <div className="text-xs font-bold">{style.name}</div>
                        <div className="text-[10px] opacity-75">{style.desc}</div>
                      </button>
                    ))}
                  </div>

                  <div>
                    <label className="text-[10px] text-gray-400 font-mono block mb-1">
                      Keyword Highlights (comma separated)
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="e.g. content, repurposing, growth, AI"
                        value={highlightKeywordsInput}
                        onChange={(e) => setHighlightKeywordsInput(e.target.value)}
                        className="w-full bg-[#111827] border border-[#1F2937] rounded-lg px-3 py-1.5 text-xs text-white placeholder-gray-600 focus:outline-none focus:border-yellow-400 font-mono"
                      />
                      <button
                        onClick={handleUpdateCaptionSettings}
                        className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-white text-xs font-semibold flex-shrink-0 transition-colors"
                      >
                        Apply
                      </button>
                    </div>
                  </div>

                  {/* Caption Action Buttons */}
                  <div className="flex items-center justify-between pt-1 border-t border-[#1F2937] text-[11px]">
                    <div className="flex items-center gap-2">
                      <a
                        href={api.getClipSrtUrl(selectedClip.id)}
                        target="_blank"
                        rel="noreferrer"
                        className="px-2.5 py-1 rounded bg-[#111827] hover:bg-gray-800 text-gray-300 border border-[#1F2937] font-mono flex items-center gap-1"
                      >
                        <Download className="w-3 h-3 text-gray-400" />
                        <span>.SRT</span>
                      </a>
                      <a
                        href={api.getClipVttUrl(selectedClip.id)}
                        target="_blank"
                        rel="noreferrer"
                        className="px-2.5 py-1 rounded bg-[#111827] hover:bg-gray-800 text-gray-300 border border-[#1F2937] font-mono flex items-center gap-1"
                      >
                        <Download className="w-3 h-3 text-gray-400" />
                        <span>.VTT</span>
                      </a>
                    </div>

                    <button
                      onClick={handleRenderCaptions}
                      disabled={isRenderingCaptions}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-yellow-500 to-amber-600 hover:opacity-90 text-black text-xs font-black shadow-md shadow-yellow-500/20 transition-all disabled:opacity-50"
                    >
                      {isRenderingCaptions ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Sparkle className="w-3.5 h-3.5" />}
                      <span>{isRenderingCaptions ? "Burning..." : "Burn Captions MP4"}</span>
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Format Pickers for Copy mode */}
            {mainStudioTab === 'copy' && (
              <div className="grid grid-cols-2 gap-2 pt-1">
                {formats.map((fmt) => {
                  const hasVar = content?.variants?.some(v => v.variant_type === fmt.variantType);
                  return (
                    <button
                      key={fmt.id}
                      onClick={() => setSelectedFormat(fmt.id)}
                      className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-all text-center flex flex-col items-center gap-0.5 ${
                        selectedFormat === fmt.id
                          ? 'bg-indigo-600/25 border-indigo-500 text-white shadow-md shadow-indigo-500/10'
                          : 'bg-[#161B26] border-[#1F2937] text-gray-400 hover:text-gray-200'
                      }`}
                    >
                      <span>{fmt.label}</span>
                      <span className={`text-[10px] ${hasVar ? 'text-emerald-400' : 'text-gray-500'}`}>
                        {hasVar ? '✓ Ready' : 'Auto-Crop'}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Collapsible Transcript Section */}
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3">
            <button
              onClick={() => setIsTranscriptExpanded(!isTranscriptExpanded)}
              className="w-full flex items-center justify-between text-left"
            >
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-400" />
                <span className="text-xs font-bold text-white uppercase tracking-wider">Source Transcript</span>
                {transcript && (
                  <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded font-mono">
                    {transcript.segments.length} segments
                  </span>
                )}
              </div>
              {isTranscriptExpanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
            </button>

            {isTranscriptExpanded && (
              <div className="pt-2 max-h-72 overflow-y-auto space-y-2 font-mono text-[11px] pr-1">
                {transcript?.segments?.length ? (
                  transcript.segments.map((seg) => (
                    <div 
                      key={seg.sequence} 
                      onClick={() => {
                        if (videoRef.current) {
                          videoRef.current.currentTime = seg.start_time;
                          videoRef.current.play().catch(() => {});
                        }
                      }}
                      className="p-2 rounded bg-[#161B26] hover:bg-[#1E2536] cursor-pointer transition-colors border border-[#1F2937] flex gap-2"
                    >
                      <span className="text-indigo-400 font-semibold flex-shrink-0">
                        [{formatSeconds(seg.start_time)} - {formatSeconds(seg.end_time)}]
                      </span>
                      <span className="text-gray-300">{seg.text}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-gray-500 italic">No timestamped transcript generated yet.</p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Column (7 cols): Mode Dependent UI & Publishing History */}
        <div className="lg:col-span-7 space-y-5">
          {mainStudioTab === 'clips' ? (
            /* Clips & Captions Mode */
            <div className="space-y-4">
              <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Film className="w-4 h-4 text-purple-400" />
                    <span className="text-xs font-bold text-white uppercase tracking-wider">Discovered Clip Candidates</span>
                  </div>
                  <span className="text-xs text-gray-400">
                    {clipsList.length} moments found
                  </span>
                </div>

                {clipsList.length === 0 ? (
                  <div className="text-center py-12 px-4 border border-dashed border-[#1F2937] rounded-xl space-y-3 bg-[#161B26]/50">
                    <Sparkles className="w-8 h-8 text-purple-400 mx-auto" />
                    <p className="text-sm font-semibold text-white">No clip candidates discovered yet</p>
                    <p className="text-xs text-gray-400 max-w-sm mx-auto">
                      Click &quot;Discover AI Clips&quot; to analyze transcript timestamps and extract high-value short-form hooks.
                    </p>
                    <button
                      onClick={handleDiscoverClips}
                      disabled={isDiscoveringClips}
                      className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold shadow-md transition-all"
                    >
                      Discover AI Clips Now
                    </button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {clipsList.map((clip) => {
                      const isSelected = selectedClip?.id === clip.id;
                      const cleanVariant = clip.variants?.find(v => !v.has_captions && (v.variant_type.includes("9_16") || v.variant_type === "MASTER"));
                      const captionedVariant = clip.variants?.find(v => v.has_captions && v.variant_type.includes("9_16")) || clip.variants?.find(v => v.has_captions);

                      return (
                        <div
                          key={clip.id}
                          onClick={() => handleSelectClip(clip)}
                          className={`p-4 rounded-xl border transition-all cursor-pointer space-y-2.5 ${
                            isSelected
                              ? 'bg-[#161B26] border-purple-500/80 shadow-lg shadow-purple-500/10'
                              : 'bg-[#161B26]/60 border-[#1F2937] hover:border-gray-600'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="space-y-1">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-bold text-white tracking-tight">{clip.title}</span>
                                <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold ${
                                  clip.status === 'READY' ? 'bg-emerald-500/20 text-emerald-300' :
                                  clip.status === 'PROCESSING' ? 'bg-amber-500/20 text-amber-300 animate-pulse' :
                                  'bg-purple-500/20 text-purple-300'
                                }`}>
                                  {clip.status}
                                </span>
                                {clip.quality_score && (
                                  <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded font-mono">
                                    Score: {clip.quality_score}
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-gray-300 italic">&ldquo;{clip.hook}&rdquo;</p>
                            </div>

                            <div className="flex items-center gap-2 flex-shrink-0">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleOpenPublishModal(clip);
                                }}
                                className="px-2.5 py-1 rounded bg-red-600/20 hover:bg-red-600/30 text-red-300 border border-red-500/30 text-xs font-bold flex items-center gap-1 transition"
                              >
                                <UploadCloud className="w-3 h-3" />
                                <span>Publish</span>
                              </button>

                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDeleteClip(clip.id);
                                }}
                                className="p-1 rounded text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>

                          <div className="flex items-center justify-between text-[11px] font-mono text-gray-400 pt-1 border-t border-[#1F2937]/70">
                            <span>
                              [{formatSeconds(clip.start_time)} - {formatSeconds(clip.end_time)}] ({(clip.end_time - clip.start_time).toFixed(1)}s)
                            </span>

                            {/* Dual Download Buttons */}
                            {clip.status === 'READY' && (
                              <div className="flex items-center gap-2">
                                {captionedVariant && (
                                  <a
                                    href={api.getClipVariantUrl(clip.id, captionedVariant.id)}
                                    target="_blank"
                                    rel="noreferrer"
                                    onClick={(e) => e.stopPropagation()}
                                    className="flex items-center gap-1 text-xs text-yellow-400 hover:text-yellow-300 font-bold bg-yellow-500/10 px-2.5 py-1 rounded border border-yellow-500/30 transition-colors"
                                  >
                                    <Download className="w-3.5 h-3.5" />
                                    <span>Captioned MP4</span>
                                  </a>
                                )}
                                {cleanVariant && (
                                  <a
                                    href={api.getClipVariantUrl(clip.id, cleanVariant.id)}
                                    target="_blank"
                                    rel="noreferrer"
                                    onClick={(e) => e.stopPropagation()}
                                    className="flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300 font-bold bg-emerald-500/10 px-2.5 py-1 rounded border border-emerald-500/20 transition-colors"
                                  >
                                    <Download className="w-3.5 h-3.5" />
                                    <span>Clean MP4</span>
                                  </a>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* Native Copy Mode */
            <>
              {brief && (
                <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-white font-bold text-xs uppercase tracking-wider">
                      <Quote className="w-4 h-4 text-indigo-400" />
                      <span>Executive Content Brief</span>
                    </div>
                    <span className="text-[10px] text-gray-500 font-mono">Phase 3 AI Analysis</span>
                  </div>

                  <p className="text-xs text-gray-300 leading-relaxed italic bg-[#161B26] p-3.5 rounded-xl border border-[#1F2937]">
                    &ldquo;{brief.summary}&rdquo;
                  </p>

                  <div className="grid grid-cols-2 gap-4 pt-1 text-xs">
                    <div>
                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1.5">Key Insights</span>
                      <ul className="space-y-1">
                        {brief.key_points.map((pt, idx) => (
                          <li key={idx} className="flex items-start gap-1.5 text-gray-300 text-[11px]">
                            <span className="text-indigo-400">•</span>
                            <span>{pt}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1.5">Themes & Topics</span>
                      <div className="flex flex-wrap gap-1.5">
                        {brief.topics.map((t, idx) => (
                          <span key={idx} className="text-[10px] bg-indigo-500/10 text-indigo-300 px-2 py-0.5 rounded-md border border-indigo-500/20 font-medium">
                            #{t}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Native Platform Copy Cards */}
              <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-4">
                <div className="flex items-center justify-between border-b border-[#1F2937] pb-3">
                  <div className="flex items-center gap-1 bg-[#161B26] p-1 rounded-xl border border-[#1F2937]">
                    {[
                      { id: 'linkedin', label: 'LinkedIn', icon: LinkedinIcon },
                      { id: 'instagram', label: 'Instagram', icon: InstagramIcon },
                      { id: 'x', label: 'X (Twitter)', icon: XIcon },
                      { id: 'youtube', label: 'YouTube', icon: YoutubeIcon }
                    ].map((tab) => {
                      const Icon = tab.icon;
                      const hasData = generatedList.some(g => g.platform.toLowerCase() === tab.id);
                      return (
                        <button
                          key={tab.id}
                          onClick={() => setActiveOutputTab(tab.id)}
                          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                            activeOutputTab === tab.id
                              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
                              : 'text-gray-400 hover:text-white'
                          }`}
                        >
                          <Icon className="w-3.5 h-3.5" />
                          <span>{tab.label}</span>
                          {hasData && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />}
                        </button>
                      );
                    })}
                  </div>

                  <button
                    onClick={() => handleRegeneratePlatform(activeOutputTab)}
                    disabled={isRegenerating}
                    className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white px-2.5 py-1.5 rounded-lg bg-[#161B26] border border-[#1F2937] transition-all disabled:opacity-50"
                  >
                    <RotateCcw className={`w-3.5 h-3.5 ${isRegenerating ? 'animate-spin text-indigo-400' : ''}`} />
                    <span>Regenerate</span>
                  </button>
                </div>

                {activeGenItem ? (
                  <div className="space-y-4 animate-fadeIn">
                    {activePayload.hook && (
                      <div className="space-y-1">
                        <span className="text-[10px] font-bold text-purple-400 uppercase tracking-wider">Hook / Angle</span>
                        <div className="p-3 bg-[#161B26] rounded-xl border border-[#1F2937] text-xs text-purple-200 font-semibold leading-relaxed">
                          {activePayload.hook}
                        </div>
                      </div>
                    )}

                    {activePayload.caption && (
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Post Caption</span>
                          <button
                            onClick={() => handleCopy(activePayload.caption, 'caption')}
                            className="flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 transition-colors"
                          >
                            {copiedKey === 'caption' ? <CheckCheck className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                            <span>{copiedKey === 'caption' ? 'Copied' : 'Copy'}</span>
                          </button>
                        </div>
                        <div className="p-3.5 bg-[#161B26] rounded-xl border border-[#1F2937] text-xs text-gray-200 whitespace-pre-wrap leading-relaxed">
                          {activePayload.caption}
                        </div>
                      </div>
                    )}

                    {activePayload.hashtags && activePayload.hashtags.length > 0 && (
                      <div className="space-y-1.5">
                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Optimized Hashtags</span>
                        <div className="flex flex-wrap gap-1.5">
                          {activePayload.hashtags.map((h: string, idx: number) => (
                            <span key={idx} className="text-xs bg-indigo-500/10 text-indigo-300 px-2 py-0.5 rounded-lg border border-indigo-500/20 font-mono">
                              #{h}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-12 border border-dashed border-[#1F2937] rounded-xl space-y-3 bg-[#161B26]/30">
                    <Sparkles className="w-8 h-8 text-indigo-400 mx-auto opacity-50" />
                    <p className="text-xs text-gray-400">No content generated for {activeOutputTab.toUpperCase()} yet.</p>
                    <button
                      onClick={() => handleRegeneratePlatform(activeOutputTab)}
                      disabled={isRegenerating}
                      className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow transition-all"
                    >
                      Generate for {activeOutputTab.toUpperCase()}
                    </button>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Phase 7: Real Publication History Section */}
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-white font-bold text-xs uppercase tracking-wider">
                <Globe className="w-4 h-4 text-emerald-400" />
                <span>Publication History</span>
              </div>
              <span className="text-xs text-gray-400">{publications.length} records</span>
            </div>

            {publications.length === 0 ? (
              <div className="text-center py-6 border border-dashed border-[#1F2937] rounded-xl text-xs text-gray-500">
                No publications sent to external platforms yet.
              </div>
            ) : (
              <div className="space-y-2.5">
                {publications.map((pub) => (
                  <div key={pub.id} className="p-3.5 rounded-xl bg-[#161B26] border border-[#1F2937] flex items-center justify-between gap-3 text-xs">
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white truncate max-w-[240px]">{pub.title}</span>
                        <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                          pub.status === 'PUBLISHED' ? 'bg-emerald-500/20 text-emerald-300' :
                          pub.status === 'UPLOADING' || pub.status === 'QUEUED' ? 'bg-amber-500/20 text-amber-300 animate-pulse' :
                          'bg-red-500/20 text-red-300'
                        }`}>
                          {pub.status}
                        </span>
                        <span className="text-[10px] text-gray-500 uppercase font-mono">
                          {pub.platform} • {pub.privacy}
                        </span>
                      </div>
                      {pub.error_message && (
                        <p className="text-[11px] text-red-400 font-mono">{pub.error_message}</p>
                      )}
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                      {pub.status === 'PUBLISHED' && pub.external_url && (
                        <a
                          href={pub.external_url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1 px-3 py-1 rounded-lg bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/30 font-bold transition"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span>View on YouTube</span>
                        </a>
                      )}

                      {pub.status === 'FAILED' && (
                        <button
                          onClick={() => handleRetryPublication(pub.id)}
                          disabled={retryingPubId === pub.id}
                          className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 font-bold transition"
                        >
                          <RefreshCw className={`w-3 h-3 ${retryingPubId === pub.id ? 'animate-spin' : ''}`} />
                          <span>Retry</span>
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Phase 7 & 8: Real Multi-Platform Social Publication Studio Modal */}
      {isPublishModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-fadeIn">
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl w-full max-w-2xl p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#1F2937] pb-3">
              <div className="flex items-center gap-2 text-white font-bold text-base">
                <Share2 className="w-5 h-5 text-indigo-400" />
                <span>Multi-Platform Publishing Studio</span>
              </div>
              <button onClick={() => setIsPublishModalOpen(false)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {publishFeedback && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-xs text-red-300">
                {publishFeedback}
              </div>
            )}

            {/* Platform Multi-Select Grid */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-gray-300 block">1. Select Target Social Destinations</label>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                {[
                  { id: 'youtube', label: 'YouTube', icon: YoutubeIcon },
                  { id: 'instagram', label: 'Instagram', icon: InstagramIcon },
                  { id: 'linkedin', label: 'LinkedIn', icon: LinkedinIcon },
                  { id: 'x', label: 'X', icon: XIcon },
                  { id: 'facebook', label: 'Facebook', icon: FacebookIcon },
                  { id: 'tiktok', label: 'TikTok', icon: TiktokIcon }
                ].map((p) => {
                  const Icon = p.icon;
                  const isSelected = selectedPlatforms.includes(p.id);
                  const isConnected = connections.some(c => c.platform.toLowerCase() === p.id && c.status === 'CONNECTED');

                  return (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => {
                        if (isSelected) {
                          if (selectedPlatforms.length > 1) {
                            setSelectedPlatforms(prev => prev.filter(x => x !== p.id));
                            if (activeModalPlatform === p.id) {
                              const remaining = selectedPlatforms.filter(x => x !== p.id);
                              setActiveModalPlatform(remaining[0] || 'youtube');
                            }
                          }
                        } else {
                          setSelectedPlatforms(prev => [...prev, p.id]);
                          setActiveModalPlatform(p.id);
                        }
                      }}
                      className={`p-2.5 rounded-xl border flex flex-col items-center gap-1.5 transition-all text-xs font-semibold ${
                        isSelected
                          ? 'bg-indigo-600/20 border-indigo-500 text-white shadow-md'
                          : isConnected
                          ? 'bg-[#161B26] border-[#1F2937] text-gray-300 hover:border-gray-600'
                          : 'bg-[#161B26]/50 border-dashed border-gray-800 text-gray-500'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      <span className="text-[11px]">{p.label}</span>
                      {isSelected ? (
                        <CheckCircle2 className="w-3 h-3 text-indigo-400" />
                      ) : isConnected ? (
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                      ) : (
                        <span className="text-[8px] text-amber-400 font-mono">Setup</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Destination Specific Editors */}
            <div className="space-y-3 bg-[#161B26] border border-[#1F2937] rounded-xl p-4">
              {/* Platform Editor Tabs */}
              <div className="flex items-center justify-between border-b border-[#1F2937] pb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-gray-300">2. Customize Metadata:</span>
                  <div className="flex items-center gap-1">
                    {selectedPlatforms.map(p => (
                      <button
                        key={p}
                        type="button"
                        onClick={() => setActiveModalPlatform(p)}
                        className={`px-2.5 py-1 rounded-lg text-[11px] font-bold uppercase tracking-wider transition ${
                          activeModalPlatform === p
                            ? 'bg-indigo-600 text-white'
                            : 'text-gray-400 hover:text-white bg-[#111827]'
                        }`}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                </div>

                <span className="text-[10px] text-emerald-400 font-mono bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  Pre-flight Verified
                </span>
              </div>

              {/* Active Platform Metadata Form */}
              {(() => {
                const p = activeModalPlatform;
                const meta = platformMetaMap[p] || { connectionId: '', title: '', description: '', tags: '', privacy: 'PRIVATE' };
                const matchingConns = connections.filter(c => c.platform.toLowerCase() === p && c.status === 'CONNECTED');

                return (
                  <div className="space-y-3 text-xs">
                    {/* Account Selector */}
                    <div>
                      <label className="text-gray-400 font-medium block mb-1">Target Connected Account</label>
                      {matchingConns.length > 0 ? (
                        <select
                          value={meta.connectionId}
                          onChange={(e) => {
                            const val = e.target.value;
                            setPlatformMetaMap(prev => ({
                              ...prev,
                              [p]: { ...meta, connectionId: val }
                            }));
                          }}
                          className="w-full bg-[#111827] border border-[#1F2937] rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500 font-medium"
                        >
                          {matchingConns.map((conn) => (
                            <option key={conn.id} value={conn.id}>
                              {conn.account_name} ({conn.handle || conn.name})
                            </option>
                          ))}
                        </select>
                      ) : (
                        <div className="p-2.5 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-center justify-between text-amber-300 text-[11px]">
                          <span className="flex items-center gap-1.5">
                            <AlertTriangle className="w-3.5 h-3.5" />
                            <span>No connected {p.toUpperCase()} account.</span>
                          </span>
                          <a href="/connections" className="underline font-bold text-white hover:text-amber-200">
                            Connect in Settings
                          </a>
                        </div>
                      )}
                    </div>

                    {/* Title (for YouTube, LinkedIn, Facebook, TikTok) */}
                    {['youtube', 'linkedin', 'facebook', 'tiktok'].includes(p) && (
                      <div>
                        <div className="flex justify-between mb-1">
                          <label className="text-gray-400 font-medium">Post Title / Hook</label>
                          <span className="text-[10px] text-gray-500 font-mono">{meta.title.length}/100</span>
                        </div>
                        <input
                          type="text"
                          maxLength={100}
                          value={meta.title}
                          onChange={(e) => {
                            const val = e.target.value;
                            setPlatformMetaMap(prev => ({
                              ...prev,
                              [p]: { ...meta, title: val }
                            }));
                          }}
                          className="w-full bg-[#111827] border border-[#1F2937] rounded-xl px-3 py-2 text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500"
                          placeholder={`Enter title for ${p}...`}
                        />
                      </div>
                    )}

                    {/* Caption / Description / Text */}
                    <div>
                      <div className="flex justify-between mb-1">
                        <label className="text-gray-400 font-medium">
                          {p === 'x' ? 'Tweet Text (max 280)' : p === 'instagram' ? 'Instagram Caption' : 'Description / Copy'}
                        </label>
                        <span className="text-[10px] text-gray-500 font-mono">
                          {meta.description.length}/{p === 'x' ? '280' : p === 'instagram' ? '2200' : '5000'}
                        </span>
                      </div>
                      <textarea
                        rows={3}
                        maxLength={p === 'x' ? 280 : p === 'instagram' ? 2200 : 5000}
                        value={meta.description}
                        onChange={(e) => {
                          const val = e.target.value;
                          setPlatformMetaMap(prev => ({
                            ...prev,
                            [p]: { ...meta, description: val }
                          }));
                        }}
                        className="w-full bg-[#111827] border border-[#1F2937] rounded-xl p-2.5 text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 resize-none font-mono text-[11px]"
                        placeholder={`Customized ${p} caption & copy...`}
                      />
                    </div>

                    {/* Tags & Privacy */}
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-gray-400 font-medium block mb-1">Hashtags / Tags</label>
                        <input
                          type="text"
                          value={meta.tags}
                          onChange={(e) => {
                            const val = e.target.value;
                            setPlatformMetaMap(prev => ({
                              ...prev,
                              [p]: { ...meta, tags: val }
                            }));
                          }}
                          className="w-full bg-[#111827] border border-[#1F2937] rounded-xl px-3 py-2 text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 font-mono text-[11px]"
                          placeholder="tag1, tag2"
                        />
                      </div>

                      <div>
                        <label className="text-gray-400 font-medium block mb-1">Privacy Level</label>
                        <select
                          value={meta.privacy}
                          onChange={(e) => {
                            const val = e.target.value as any;
                            setPlatformMetaMap(prev => ({
                              ...prev,
                              [p]: { ...meta, privacy: val }
                            }));
                          }}
                          className="w-full bg-[#111827] border border-[#1F2937] rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500 font-bold"
                        >
                          <option value="PRIVATE">🔒 Private / Self-Only</option>
                          <option value="UNLISTED">🔗 Unlisted</option>
                          <option value="PUBLIC">🌐 Public</option>
                        </select>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-between pt-3 border-t border-[#1F2937]">
              <span className="text-[11px] text-gray-500 flex items-center gap-1">
                <Lock className="w-3 h-3 text-emerald-400" />
                <span>Zero Plaintext Token Storage</span>
              </span>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsPublishModalOpen(false)}
                  className="px-3.5 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-semibold transition"
                >
                  Cancel
                </button>

                <button
                  onClick={handleConfirmPublish}
                  disabled={isPublishing || selectedPlatforms.length === 0}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-md shadow-indigo-600/30 transition disabled:opacity-50"
                >
                  {isPublishing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <UploadCloud className="w-3.5 h-3.5" />}
                  <span>{isPublishing ? "Dispatching Jobs..." : `Publish to ${selectedPlatforms.length} Platform(s)`}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function RepurposePage() {
  return (
    <Suspense fallback={<div className="p-8 text-xs text-gray-500 font-mono">Loading Repurpose Studio...</div>}>
      <RepurposeContent />
    </Suspense>
  );
}
