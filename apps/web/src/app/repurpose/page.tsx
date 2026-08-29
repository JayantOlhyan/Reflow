"use client";

import React, { useState, useEffect, Suspense } from 'react';
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
  CheckCircle2
} from 'lucide-react';
import { YoutubeIcon, InstagramIcon, TiktokIcon, LinkedinIcon, XIcon, FacebookIcon } from '@/components/ui/SocialIcons';
import { ContentItem, ContentVariant, Transcript, ContentBrief, GeneratedContent } from '@/types';
import { api } from '@/lib/api';

function RepurposeContent() {
  const searchParams = useSearchParams();
  const contentId = searchParams.get('id');

  const [content, setContent] = useState<ContentItem | null>(null);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [brief, setBrief] = useState<ContentBrief | null>(null);
  const [generatedList, setGeneratedList] = useState<GeneratedContent[]>([]);
  const [selectedFormat, setSelectedFormat] = useState('9:16');
  const [activeOutputTab, setActiveOutputTab] = useState('linkedin');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);
  const [isTranscriptExpanded, setIsTranscriptExpanded] = useState(false);

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
    } catch (e) {
      console.warn("Failed to load content data:", e);
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

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            {content ? content.title : "Repurpose Studio"}
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            {primaryAsset?.original_filename || "Transform video assets into platform-tailored intelligence and native copies."}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleGenerateAll}
            disabled={isGenerating}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 via-purple-600 to-cyan-500 hover:opacity-95 text-white text-xs font-bold shadow-lg shadow-indigo-500/25 transition-all disabled:opacity-50"
          >
            {isGenerating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            <span>{isGenerating ? "Synthesizing AI Engine..." : "Synthesize Platform Outputs"}</span>
          </button>
        </div>
      </div>

      {actionFeedback && (
        <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-xl p-3.5 text-xs text-indigo-300 flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-indigo-400 flex-shrink-0" />
            <span>{actionFeedback}</span>
          </div>
          <button onClick={() => setActionFeedback(null)} className="text-gray-400 hover:text-white font-semibold">✕</button>
        </div>
      )}

      {/* Main Grid: Media Left, Content Brief & Platform Outputs Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (5 cols): Media Player & Transcript */}
        <div className="lg:col-span-5 space-y-5">
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
                {matchedVariant ? `Variant (${selectedFormat})` : "Source Video"}
              </span>
              <span className="text-[11px] text-gray-400 bg-[#161B26] px-2 py-0.5 rounded border border-[#1F2937] font-mono">
                {matchedVariant ? `${matchedVariant.width}x${matchedVariant.height}` : primaryAsset ? `${primaryAsset.width || 1920}x${primaryAsset.height || 1080}` : '1080p'}
              </span>
            </div>

            <div className="relative aspect-video bg-[#0B0D12] rounded-xl overflow-hidden border border-[#1F2937]/80 flex items-center justify-center">
              {activeMediaUrl ? (
                <video src={activeMediaUrl} controls className="w-full h-full object-contain" />
              ) : (
                <div className="text-xs text-gray-500 flex items-center gap-2">
                  <Play className="w-4 h-4" />
                  <span>No media stream available</span>
                </div>
              )}
            </div>

            {/* Format Pickers */}
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
                    <div key={seg.sequence} className="p-2 rounded bg-[#161B26] border border-[#1F2937] flex gap-2">
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

        {/* Right Column (7 cols): Content Intelligence Brief & Platform Native Generators */}
        <div className="lg:col-span-7 space-y-5">
          {/* Content Brief Card */}
          {brief && (
            <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-white font-bold text-xs uppercase tracking-wider">
                  <Sparkles className="w-4 h-4 text-purple-400" />
                  <span>Content Intelligence Brief</span>
                </div>
                <span className="text-[10px] text-purple-300 bg-purple-500/20 px-2 py-0.5 rounded border border-purple-500/30">
                  {brief.tone} • {brief.audience}
                </span>
              </div>

              <p className="text-xs text-gray-300 leading-relaxed bg-[#161B26] p-3 rounded-xl border border-[#1F2937]">
                {brief.summary}
              </p>

              {brief.key_points?.length > 0 && (
                <div className="space-y-1">
                  <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Key Takeaways</span>
                  <div className="grid grid-cols-1 gap-1.5 pt-1">
                    {brief.key_points.map((pt, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-xs text-gray-300">
                        <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-1.5 flex-shrink-0" />
                        <span>{pt}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Platform Outputs */}
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-1 bg-[#161B26] p-1 rounded-xl border border-[#1F2937] overflow-x-auto">
                {[
                  { key: 'linkedin', label: 'LinkedIn', icon: LinkedinIcon, color: 'text-blue-400' },
                  { key: 'instagram', label: 'Instagram', icon: InstagramIcon, color: 'text-pink-400' },
                  { key: 'x', label: 'X (Twitter)', icon: XIcon, color: 'text-gray-300' },
                  { key: 'youtube', label: 'YouTube', icon: YoutubeIcon, color: 'text-red-400' },
                ].map((plt) => {
                  const Icon = plt.icon;
                  const isSelected = activeOutputTab === plt.key;
                  return (
                    <button
                      key={plt.key}
                      onClick={() => setActiveOutputTab(plt.key)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                        isSelected ? 'bg-indigo-600 text-white shadow-sm' : 'text-gray-400 hover:text-white'
                      }`}
                    >
                      <Icon className={`w-3.5 h-3.5 ${plt.color}`} />
                      <span>{plt.label}</span>
                    </button>
                  );
                })}
              </div>

              <button
                onClick={() => handleRegeneratePlatform(activeOutputTab)}
                disabled={isRegenerating}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#161B26] border border-[#1F2937] hover:border-gray-600 text-gray-300 hover:text-white text-xs font-medium transition-all"
              >
                <RotateCcw className={`w-3.5 h-3.5 ${isRegenerating ? 'animate-spin' : ''}`} />
                <span>Regenerate</span>
              </button>
            </div>

            {/* Platform Specific Output Body */}
            {activeOutputTab === 'linkedin' && (
              <div className="bg-[#161B26] border border-[#1F2937] rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white uppercase">LinkedIn Post (Hook + Body + CTA)</span>
                  <button
                    onClick={() => handleCopy(`${activePayload.hook || ''}\n\n${activePayload.body || ''}\n\n${activePayload.call_to_action || ''}`, 'linkedin')}
                    className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                  >
                    {copiedKey === 'linkedin' ? <CheckCheck className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedKey === 'linkedin' ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
                <p className="text-xs font-bold text-indigo-300">{activePayload.hook || "Generated Hook"}</p>
                <p className="text-xs text-gray-300 whitespace-pre-line leading-relaxed">{activePayload.body || "Generated LinkedIn Post body..."}</p>
                <p className="text-xs font-semibold text-emerald-400">{activePayload.call_to_action || ""}</p>
                {activePayload.hashtags && (
                  <p className="text-[11px] text-cyan-400 font-mono">{activePayload.hashtags.join(' ')}</p>
                )}
              </div>
            )}

            {activeOutputTab === 'instagram' && (
              <div className="bg-[#161B26] border border-[#1F2937] rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white uppercase">Instagram Reel Caption</span>
                  <button
                    onClick={() => handleCopy(`${activePayload.caption || ''}\n\n${(activePayload.hashtags || []).join(' ')}`, 'instagram')}
                    className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                  >
                    {copiedKey === 'instagram' ? <CheckCheck className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedKey === 'instagram' ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
                <p className="text-xs font-bold text-pink-400">{activePayload.hook || ""}</p>
                <p className="text-xs text-gray-300 whitespace-pre-line leading-relaxed">{activePayload.caption || "Generated Instagram Reel caption..."}</p>
                {activePayload.hashtags && (
                  <p className="text-[11px] text-cyan-400 font-mono">{activePayload.hashtags.join(' ')}</p>
                )}
              </div>
            )}

            {activeOutputTab === 'x' && (
              <div className="bg-[#161B26] border border-[#1F2937] rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white uppercase">
                    {activePayload.posts ? `X Thread (${activePayload.posts.length} Tweets)` : 'X Post'}
                  </span>
                  <button
                    onClick={() => handleCopy(activePayload.posts ? activePayload.posts.join('\n\n---\n\n') : activePayload.post_text || '', 'x')}
                    className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                  >
                    {copiedKey === 'x' ? <CheckCheck className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedKey === 'x' ? 'Copied' : 'Copy Thread'}</span>
                  </button>
                </div>
                {activePayload.posts ? (
                  <div className="space-y-2">
                    {activePayload.posts.map((tweet: string, idx: number) => (
                      <div key={idx} className="p-3 bg-[#111827] rounded-lg border border-[#1F2937] space-y-1">
                        <div className="flex items-center justify-between text-[10px] text-gray-500 font-mono">
                          <span>Tweet {idx + 1} of {activePayload.posts.length}</span>
                          <span className={tweet.length > 280 ? 'text-rose-400' : 'text-emerald-400'}>
                            {tweet.length} / 280 chars
                          </span>
                        </div>
                        <p className="text-xs text-gray-200 whitespace-pre-line">{tweet}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-300 whitespace-pre-line">{activePayload.post_text || "Generated X tweet..."}</p>
                )}
              </div>
            )}

            {activeOutputTab === 'youtube' && (
              <div className="bg-[#161B26] border border-[#1F2937] rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white uppercase">YouTube Metadata & Chapters</span>
                  <button
                    onClick={() => handleCopy(`${activePayload.title || ''}\n\n${activePayload.description || ''}`, 'youtube')}
                    className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                  >
                    {copiedKey === 'youtube' ? <CheckCheck className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedKey === 'youtube' ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
                <div>
                  <span className="text-[10px] text-gray-500 font-mono block">Title</span>
                  <p className="text-xs font-bold text-white">{activePayload.title || "YouTube Title"}</p>
                </div>
                <div>
                  <span className="text-[10px] text-gray-500 font-mono block">Description</span>
                  <p className="text-xs text-gray-300 whitespace-pre-line leading-relaxed">{activePayload.description || "Description..."}</p>
                </div>
                {activePayload.chapters?.length > 0 && (
                  <div className="space-y-1 pt-1">
                    <span className="text-[10px] text-gray-500 font-mono block">Timestamped Chapters</span>
                    <div className="space-y-1">
                      {activePayload.chapters.map((ch: any, idx: number) => (
                        <div key={idx} className="flex items-center gap-2 text-xs font-mono">
                          <span className="text-red-400 font-bold">{ch.timestamp}</span>
                          <span className="text-gray-300">{ch.title}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function RepurposeEditorPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs text-gray-500">Loading Studio...</div>}>
      <RepurposeContent />
    </Suspense>
  );
}
