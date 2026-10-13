"use client";

import React, { useState, useEffect, useRef } from 'react';
import { 
  LayoutTemplate, 
  Plus, 
  Volume2, 
  Sliders, 
  Trash2, 
  RefreshCw, 
  Check, 
  Sparkles, 
  Film, 
  Layers, 
  Play, 
  Pause, 
  ArrowRight,
  ExternalLink,
  X,
  Palette,
  Eye,
  Type,
  Maximize2,
  Smartphone,
  Monitor,
  Square,
  ShieldAlert,
  SlidersHorizontal,
  Flame,
  CheckCircle2,
  Radio,
  Zap,
  Music,
  Heart,
  MessageCircle,
  Share,
  Bookmark
} from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { AudiogramTemplateItem } from '@/types';

const CURATED_PALETTES = [
  { name: 'Electric Indigo', wave: '#6366F1', bg: '#080B14' },
  { name: 'Hormozi Gold', wave: '#FACC15', bg: '#09090B' },
  { name: 'Cyber Cyan', wave: '#06B6D4', bg: '#04131D' },
  { name: 'Sunset Pink', wave: '#EC4899', bg: '#140614' },
  { name: 'Emerald Signal', wave: '#10B981', bg: '#041711' },
  { name: 'Obsidian White', wave: '#FFFFFF', bg: '#0A0A0A' },
];

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<AudiogramTemplateItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'all' | 'audiograms' | 'video'>('all');

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isPlayingAudio, setIsPlayingAudio] = useState(true);
  const [showSafeZoneOverlay, setShowSafeZoneOverlay] = useState(false);

  // Template Form State
  const [name, setName] = useState('');
  const [aspectRatio, setAspectRatio] = useState<'9:16' | '1:1' | '16:9' | '4:5'>('9:16');
  const [waveformStyle, setWaveformStyle] = useState<'BARS' | 'LINE' | 'CIRCULAR' | 'EQUALIZER' | 'WAVE'>('BARS');
  const [waveformColor, setWaveformColor] = useState('#6366F1');
  const [backgroundColor, setBackgroundColor] = useState('#080B14');
  const [titleTemplate, setTitleTemplate] = useState('Episode {{title}} — The Breakthrough');
  const [showProgressBar, setShowProgressBar] = useState(true);
  const [progressBarColor, setProgressBarColor] = useState('#10B981');
  const [captionStyle, setCaptionStyle] = useState<'BOLD_PUNCH' | 'CLEAN_SUB' | 'NEON_GLOW'>('BOLD_PUNCH');

  // Animation Canvas Ref
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    setIsLoading(true);
    try {
      const data = await api.getAudiogramTemplates();
      setTemplates(data || []);
    } catch (err) {
      console.error("Failed to load templates:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setIsSubmitting(true);
    try {
      await api.createAudiogramTemplate({
        name,
        aspect_ratio: aspectRatio,
        waveform_style: waveformStyle,
        waveform_color: waveformColor,
        background_color: backgroundColor,
        title_template: titleTemplate,
        show_progress_bar: showProgressBar,
        progress_bar_color: progressBarColor,
        caption_style: captionStyle,
      });

      setIsModalOpen(false);
      resetForm();
      await loadTemplates();
    } catch (err) {
      console.error("Failed to create template:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteTemplate = async (id: string) => {
    if (!confirm("Are you sure you want to delete this template preset?")) return;
    try {
      await api.deleteAudiogramTemplate(id);
      setTemplates(prev => prev.filter(t => t.id !== id));
    } catch (err) {
      console.error("Failed to delete template:", err);
    }
  };

  const resetForm = () => {
    setName('');
    setAspectRatio('9:16');
    setWaveformStyle('BARS');
    setWaveformColor('#6366F1');
    setBackgroundColor('#080B14');
    setTitleTemplate('Episode {{title}} — The Breakthrough');
    setShowProgressBar(true);
    setProgressBarColor('#10B981');
    setCaptionStyle('BOLD_PUNCH');
  };

  const applyPalette = (wave: string, bg: string) => {
    setWaveformColor(wave);
    setBackgroundColor(bg);
  };

  // High-Fidelity Animated Canvas Waveform Engine
  useEffect(() => {
    if (!isModalOpen) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let step = 0;

    const render = () => {
      step += 0.045;
      const width = canvas.width;
      const height = canvas.height;

      ctx.clearRect(0, 0, width, height);

      // Deep Studio Background
      ctx.fillStyle = backgroundColor;
      ctx.fillRect(0, 0, width, height);

      // Ambient Acoustic Spotlight Glow
      const glow = ctx.createRadialGradient(
        width / 2, height / 2, 10,
        width / 2, height / 2, width * 0.6
      );
      glow.addColorStop(0, `${waveformColor}33`);
      glow.addColorStop(0.6, `${waveformColor}0A`);
      glow.addColorStop(1, 'transparent');
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, width, height);

      // Artwork Avatar Frame Simulation
      const avatarSize = Math.min(width * 0.42, 120);
      const avatarY = height * 0.28;
      
      // Avatar shadow
      ctx.fillStyle = 'rgba(0,0,0,0.6)';
      ctx.beginPath();
      ctx.roundRect(width / 2 - avatarSize / 2, avatarY - avatarSize / 2 + 6, avatarSize, avatarSize, 16);
      ctx.fill();

      // Avatar background
      const avatarGrad = ctx.createLinearGradient(
        width / 2 - avatarSize / 2, avatarY - avatarSize / 2,
        width / 2 + avatarSize / 2, avatarY + avatarSize / 2
      );
      avatarGrad.addColorStop(0, '#1E293B');
      avatarGrad.addColorStop(1, '#0F172A');
      ctx.fillStyle = avatarGrad;
      ctx.beginPath();
      ctx.roundRect(width / 2 - avatarSize / 2, avatarY - avatarSize / 2, avatarSize, avatarSize, 16);
      ctx.fill();

      // Avatar Border
      ctx.strokeStyle = 'rgba(255,255,255,0.15)';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Audio Icon in Avatar
      ctx.fillStyle = waveformColor;
      ctx.font = 'bold 24px system-ui';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('🎙️', width / 2, avatarY);

      // Episode Title Text Overlay
      ctx.fillStyle = '#FFFFFF';
      ctx.font = 'bold 12px "Plus Jakarta Sans", sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      const cleanTitle = titleTemplate.replace('{{title}}', 'The Billion Dollar Lesson');
      ctx.fillText(cleanTitle, width / 2, avatarY + avatarSize / 2 + 16);

      // Subtitle Preview
      const subY = height * 0.76;
      if (captionStyle === 'BOLD_PUNCH') {
        ctx.fillStyle = '#FACC15'; // Hormozi Punch Yellow
        ctx.font = '900 13px "Space Grotesk", sans-serif';
        ctx.fillText('"DON\'T BUILD FEATURES..."', width / 2, subY);
        ctx.fillStyle = '#FFFFFF';
        ctx.fillText('"BUILD AUDIENCE LEVERAGE."', width / 2, subY + 18);
      } else if (captionStyle === 'NEON_GLOW') {
        ctx.fillStyle = '#06B6D4';
        ctx.font = 'bold 12px "Space Grotesk", sans-serif';
        ctx.shadowColor = '#06B6D4';
        ctx.shadowBlur = 8;
        ctx.fillText('“Focus on distribution from Day 1.”', width / 2, subY);
        ctx.shadowBlur = 0;
      } else {
        ctx.fillStyle = '#E2E8F0';
        ctx.font = '500 11px "Plus Jakarta Sans", sans-serif';
        ctx.fillText('“Focus on distribution from Day 1.”', width / 2, subY);
      }

      // Waveform Rendering
      const centerY = height * 0.58;
      ctx.fillStyle = waveformColor;
      ctx.strokeStyle = waveformColor;
      ctx.lineWidth = 3;

      if (waveformStyle === 'BARS' || waveformStyle === 'EQUALIZER') {
        const barCount = 26;
        const barWidth = 3.5;
        const totalW = width * 0.75;
        const spacing = totalW / barCount;
        const startX = (width - totalW) / 2;

        for (let i = 0; i < barCount; i++) {
          const factor = isPlayingAudio 
            ? Math.sin(step * 2.2 + i * 0.45) * 0.45 + Math.cos(step * 3.4 + i * 0.35) * 0.45 + 0.1
            : 0.1;
          const barHeight = Math.max(6, Math.abs(factor) * (height * 0.14));
          const x = startX + i * spacing;
          const y = centerY - barHeight / 2;

          ctx.beginPath();
          ctx.roundRect(x, y, barWidth, barHeight, 2);
          ctx.fill();
        }
      } else if (waveformStyle === 'LINE' || waveformStyle === 'WAVE') {
        ctx.beginPath();
        const startX = width * 0.15;
        const endX = width * 0.85;
        for (let x = startX; x <= endX; x += 3) {
          const factor = isPlayingAudio 
            ? Math.sin((x / 18) + step * 2.5) * Math.cos((x / 32) + step) 
            : 0.05;
          const y = centerY + factor * (height * 0.08);
          if (x === startX) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      } else if (waveformStyle === 'CIRCULAR') {
        const radius = Math.min(width, height) * 0.12;
        const points = 32;

        ctx.beginPath();
        for (let i = 0; i <= points; i++) {
          const angle = (i / points) * Math.PI * 2;
          const factor = isPlayingAudio 
            ? Math.sin(step * 3 + i * 0.8) * 8 
            : 2;
          const r = radius + factor;
          const x = width / 2 + Math.cos(angle) * r;
          const y = centerY + Math.sin(angle) * r;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.stroke();
      }

      // Audio Progress Bar
      if (showProgressBar) {
        const barY = height * 0.92;
        const barMargin = width * 0.12;
        const barW = width - barMargin * 2;
        
        ctx.fillStyle = 'rgba(255, 255, 255, 0.12)';
        ctx.beginPath();
        ctx.roundRect(barMargin, barY, barW, 3, 2);
        ctx.fill();

        ctx.fillStyle = progressBarColor;
        const progressFrac = ((Math.sin(step * 0.3) + 1) / 2);
        ctx.beginPath();
        ctx.roundRect(barMargin, barY, progressFrac * barW, 3, 2);
        ctx.fill();

        // Time indicators
        ctx.fillStyle = '#64748B';
        ctx.font = '8px "JetBrains Mono", monospace';
        ctx.textAlign = 'left';
        ctx.fillText('0:14', barMargin, barY + 9);
        ctx.textAlign = 'right';
        ctx.fillText('0:45', width - barMargin, barY + 9);
      }

      animationFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [
    isModalOpen, 
    waveformStyle, 
    waveformColor, 
    backgroundColor, 
    titleTemplate, 
    showProgressBar, 
    progressBarColor, 
    isPlayingAudio,
    captionStyle,
    aspectRatio
  ]);

  const filteredTemplates = templates.filter(t => {
    if (activeTab === 'audiograms') return true;
    if (activeTab === 'video') return t.aspect_ratio === '9:16' || t.aspect_ratio === '16:9';
    return true;
  });

  return (
    <div className="space-y-8 animate-fadeIn pb-20">
      {/* Editorial Header */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-5 border-b border-white/[0.06] pb-6">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-widest bg-purple-500/10 text-purple-400 border border-purple-500/20 font-semibold">
              Creative Studio
            </span>
            <span className="text-xs text-gray-500 font-mono">•</span>
            <span className="text-xs text-gray-400 font-medium">Repurpose.io Template Engine</span>
          </div>
          <h1 className="text-3xl font-bold font-display text-white tracking-tight">
            Creative Templates Studio
          </h1>
          <p className="text-sm text-gray-400 max-w-2xl leading-relaxed">
            Craft reusable visual audiograms and vertical video frames with kinetic soundwaves, progress timers, and subtitle typography presets.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={loadTemplates}
            className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.08] text-gray-300 text-xs font-medium transition-all shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-purple-500 via-purple-600 to-indigo-600 hover:from-purple-400 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-purple-500/25 transition-all transform hover:-translate-y-0.5"
          >
            <Plus className="w-4 h-4" />
            <span>Create Preset</span>
          </button>
        </div>
      </div>

      {/* Tabs Filter Bar */}
      <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-white/[0.03] border border-white/[0.06]">
          {(['all', 'audiograms', 'video'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === tab
                  ? 'bg-purple-600 text-white shadow-sm'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab === 'all' && `All Presets (${templates.length})`}
              {tab === 'audiograms' && 'Audiogram Soundwaves'}
              {tab === 'video' && 'Video Framing (9:16)'}
            </button>
          ))}
        </div>

        <Link
          href="/workflows"
          className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-medium"
        >
          <span>Use in Automated Workflows</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* Templates Grid with Visual Cards */}
      {filteredTemplates.length === 0 ? (
        <div className="surface-card rounded-3xl p-12 text-center space-y-4 border-dashed">
          <div className="w-14 h-14 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center mx-auto text-purple-400">
            <LayoutTemplate className="w-7 h-7" />
          </div>
          <div className="max-w-md mx-auto space-y-1">
            <h3 className="text-lg font-bold font-display text-white">No custom templates saved</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Design your first custom Audiogram or video preset with tailored soundwave frequencies, typography, and aspect ratios.
            </p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-md transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Launch Template Studio</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTemplates.map(tmpl => (
            <div
              key={tmpl.id}
              className="surface-card surface-card-hover rounded-2xl p-4 flex flex-col justify-between space-y-4 shadow-md group relative overflow-hidden"
            >
              {/* Studio Canvas Preview Box */}
              <div 
                className="w-full h-48 rounded-xl flex flex-col items-center justify-center relative overflow-hidden border border-white/10 shadow-inner"
                style={{ backgroundColor: tmpl.background_color || '#080B14' }}
              >
                {/* Ambient glow in card */}
                <div 
                  className="absolute inset-0 opacity-20 pointer-events-none"
                  style={{
                    background: `radial-gradient(circle at center, ${tmpl.waveform_color || '#6366F1'} 0%, transparent 70%)`
                  }}
                />

                {/* Simulated Audio Spectrum Visualizer */}
                <div className="flex items-center justify-center gap-1.5 h-16 w-3/4 z-10">
                  {[22, 45, 28, 65, 85, 42, 70, 35, 55, 26, 75, 38, 60, 30].map((h, i) => (
                    <div
                      key={i}
                      className="w-1 rounded-full transition-all duration-300"
                      style={{
                        height: `${h}%`,
                        backgroundColor: tmpl.waveform_color || '#6366F1'
                      }}
                    />
                  ))}
                </div>

                {/* Title badge in card */}
                <div className="absolute top-3 inset-x-3 text-center z-10">
                  <span className="text-[11px] font-bold font-display text-white truncate block px-2 drop-shadow-md">
                    {tmpl.title_template || tmpl.name}
                  </span>
                </div>

                {/* Aspect ratio badge */}
                <div className="absolute bottom-3 left-3 flex items-center gap-1.5 bg-black/75 backdrop-blur-md px-2 py-0.5 rounded-md border border-white/10 text-[10px] font-mono text-gray-300 font-semibold z-10">
                  <Maximize2 className="w-3 h-3 text-purple-400" />
                  <span>{tmpl.aspect_ratio}</span>
                </div>

                {/* Style badge */}
                <div className="absolute bottom-3 right-3 bg-black/75 backdrop-blur-md px-2 py-0.5 rounded-md border border-white/10 text-[10px] font-mono text-gray-300 font-semibold z-10">
                  <span>{tmpl.waveform_style}</span>
                </div>
              </div>

              {/* Template Info & Actions */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold font-display text-white tracking-tight">{tmpl.name}</h3>
                    <div className="flex items-center gap-2 mt-1 font-mono text-[11px] text-gray-400">
                      <span className="w-2.5 h-2.5 rounded-full border border-white/20 shadow-sm" style={{ backgroundColor: tmpl.waveform_color }} />
                      <span>{tmpl.waveform_color}</span>
                      <span className="text-gray-600">•</span>
                      <span className="capitalize">{tmpl.caption_style.toLowerCase().replace('_', ' ')}</span>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDeleteTemplate(tmpl.id)}
                    className="p-1.5 rounded-xl text-gray-500 hover:text-red-400 hover:bg-white/[0.04] transition-all opacity-0 group-hover:opacity-100"
                    title="Delete template preset"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-white/[0.06] text-xs">
                  <Link
                    href={`/workflows`}
                    className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                  >
                    <span>Use in Workflow</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>

                  <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wider font-semibold">
                    Studio Ready
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ========================================================================= */}
      {/* INTERACTIVE HIGH-END TEMPLATE DESIGNER STUDIO MODAL                       */}
      {/* ========================================================================= */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/85 backdrop-blur-xl animate-fadeIn">
          <div className="surface-elevated rounded-3xl w-full max-w-4xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden border border-white/10">
            {/* Modal Header */}
            <div className="p-5 border-b border-white/[0.08] flex items-center justify-between bg-[#080B11]">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-xl bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-purple-400">
                  <Palette className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-lg font-bold font-display text-white">Audiogram & Video Frame Studio</h3>
                  <p className="text-xs text-gray-400">Real-time acoustic visualizer with phone device simulation and safe-zone guides.</p>
                </div>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1.5 rounded-xl text-gray-400 hover:text-white hover:bg-white/[0.08]"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Split Layout: Device Canvas Preview on Left, Studio Controls on Right */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 overflow-y-auto flex-1 bg-[#0B0E17]">
              {/* Left Column: Device Mockup Preview (5 cols) */}
              <div className="lg:col-span-5 flex flex-col items-center justify-center bg-[#07090F] border border-white/[0.08] rounded-2xl p-4 space-y-3">
                <div className="flex items-center justify-between w-full px-1">
                  <span className="text-[11px] font-mono uppercase font-bold text-gray-400 tracking-wider flex items-center gap-1.5">
                    <Eye className="w-3.5 h-3.5 text-purple-400" />
                    Live Canvas Preview
                  </span>

                  <div className="flex items-center gap-2">
                    {/* Safe Zone Toggle for 9:16 */}
                    {aspectRatio === '9:16' && (
                      <button
                        type="button"
                        onClick={() => setShowSafeZoneOverlay(!showSafeZoneOverlay)}
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium transition-all ${
                          showSafeZoneOverlay 
                            ? 'bg-purple-600 text-white' 
                            : 'bg-white/[0.04] text-gray-400 hover:text-white'
                        }`}
                        title="Display TikTok / Reels safe-zones overlay"
                      >
                        Safe Zones
                      </button>
                    )}

                    <button
                      onClick={() => setIsPlayingAudio(!isPlayingAudio)}
                      className="flex items-center gap-1 px-2 py-0.5 rounded-lg bg-white/[0.04] text-gray-300 text-[10px] font-mono font-semibold hover:text-white"
                    >
                      {isPlayingAudio ? (
                        <>
                          <Pause className="w-3 h-3 text-amber-400" />
                          <span>Pause</span>
                        </>
                      ) : (
                        <>
                          <Play className="w-3 h-3 text-emerald-400" />
                          <span>Play</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Smartphone Device Frame for 9:16 vertical */}
                <div className="relative flex items-center justify-center w-full min-h-[380px]">
                  {aspectRatio === '9:16' ? (
                    <div className="relative rounded-[36px] p-2 bg-[#1C1F2B] border-2 border-[#2E344A] shadow-2xl overflow-hidden">
                      {/* Dynamic Island Pill */}
                      <div className="absolute top-3 inset-x-0 mx-auto w-16 h-3 bg-black rounded-full z-30" />

                      {/* Phone Screen Canvas */}
                      <div className="relative rounded-[28px] overflow-hidden">
                        <canvas
                          ref={canvasRef}
                          width={210}
                          height={370}
                          className="block rounded-[28px]"
                        />

                        {/* TikTok / Reels Overlay Guide */}
                        {showSafeZoneOverlay && (
                          <div className="absolute inset-0 pointer-events-none flex flex-col justify-between p-3 z-20 text-[9px] font-mono">
                            <div className="w-full text-center text-amber-400/80 bg-black/40 py-0.5 rounded border border-amber-400/30">
                              Header Safe Area
                            </div>
                            <div className="flex justify-end gap-1">
                              <div className="space-y-2 text-right text-gray-400 pr-1 flex flex-col items-center">
                                <Heart className="w-4 h-4 text-white/70" />
                                <MessageCircle className="w-4 h-4 text-white/70" />
                                <Bookmark className="w-4 h-4 text-white/70" />
                                <Share className="w-4 h-4 text-white/70" />
                              </div>
                            </div>
                            <div className="w-full text-amber-400/80 bg-black/40 py-1 px-2 rounded border border-amber-400/30">
                              Caption & Sound Title Safe Zone
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-2xl p-2 bg-black/40 border border-white/10 shadow-2xl">
                      <canvas
                        ref={canvasRef}
                        width={aspectRatio === '1:1' ? 290 : 330}
                        height={aspectRatio === '1:1' ? 290 : 190}
                        className="rounded-xl shadow-lg"
                      />
                    </div>
                  )}
                </div>

                <div className="text-[10px] text-gray-500 font-mono text-center">
                  Live acoustic rendering at 60 FPS • {aspectRatio}
                </div>
              </div>

              {/* Right Column: Studio Controls (7 cols) */}
              <form onSubmit={handleCreateTemplate} className="lg:col-span-7 space-y-4">
                {/* Template Name */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300">Preset Title</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Electric Cyan Vertical Hook (9:16)"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/[0.08] text-white text-xs focus:outline-none focus:border-purple-500"
                  />
                </div>

                {/* Aspect Ratio Selector */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300">Canvas Dimensions</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { id: '9:16', label: '9:16 Vertical', icon: Smartphone, sub: 'Shorts & Reels' },
                      { id: '1:1', label: '1:1 Square', icon: Square, sub: 'Feed Posts' },
                      { id: '16:9', label: '16:9 Landscape', icon: Monitor, sub: 'YouTube 4K' }
                    ].map(ar => {
                      const Icon = ar.icon;
                      return (
                        <button
                          type="button"
                          key={ar.id}
                          onClick={() => setAspectRatio(ar.id as any)}
                          className={`p-2.5 rounded-xl border text-center transition-all ${
                            aspectRatio === ar.id
                              ? 'bg-purple-600/25 border-purple-500 text-white font-semibold shadow-sm'
                              : 'bg-white/[0.02] border-white/[0.06] text-gray-400 hover:text-white'
                          }`}
                        >
                          <Icon className="w-4 h-4 mx-auto mb-1 text-purple-400" />
                          <div className="text-xs font-bold font-display">{ar.label}</div>
                          <div className="text-[10px] text-gray-500 font-mono mt-0.5">{ar.sub}</div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Soundwave Style Selector */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300">Waveform Engine</label>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {[
                      { id: 'BARS', label: 'Equalizer Bars' },
                      { id: 'LINE', label: 'Oscilloscope' },
                      { id: 'CIRCULAR', label: 'Audio Ring' },
                      { id: 'WAVE', label: 'Smooth Sine' }
                    ].map(style => (
                      <button
                        type="button"
                        key={style.id}
                        onClick={() => setWaveformStyle(style.id as any)}
                        className={`px-3 py-2 rounded-xl border text-xs font-medium text-center transition-all ${
                          waveformStyle === style.id
                            ? 'bg-purple-600/25 border-purple-500 text-white font-semibold'
                            : 'bg-white/[0.02] border-white/[0.06] text-gray-400 hover:text-white'
                        }`}
                      >
                        {style.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Curated Color Palettes */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-semibold text-gray-300">Curated Creator Palettes</label>
                    <span className="text-[10px] font-mono text-gray-500">1-Click Apply</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {CURATED_PALETTES.map(p => (
                      <button
                        type="button"
                        key={p.name}
                        onClick={() => applyPalette(p.wave, p.bg)}
                        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs transition-all ${
                          waveformColor === p.wave
                            ? 'border-purple-400 bg-purple-500/10 text-white font-semibold'
                            : 'border-white/[0.08] bg-black/40 text-gray-400 hover:text-white'
                        }`}
                      >
                        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: p.wave }} />
                        <span>{p.name}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Subtitle / Caption Typography Preset */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300">Subtitle Typography Preset</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { id: 'BOLD_PUNCH', label: 'Bold Punch', desc: 'Yellow Hormozi Punch' },
                      { id: 'NEON_GLOW', label: 'Neon Glow', desc: 'Glowing Cyber Cyan' },
                      { id: 'CLEAN_SUB', label: 'Clean Editorial', desc: 'Minimalist Sans' }
                    ].map(cap => (
                      <button
                        type="button"
                        key={cap.id}
                        onClick={() => setCaptionStyle(cap.id as any)}
                        className={`p-2 rounded-xl border text-left transition-all ${
                          captionStyle === cap.id
                            ? 'bg-purple-600/25 border-purple-500 text-white font-semibold'
                            : 'bg-white/[0.02] border-white/[0.06] text-gray-400 hover:text-white'
                        }`}
                      >
                        <div className="text-xs font-bold">{cap.label}</div>
                        <div className="text-[10px] text-gray-500 mt-0.5">{cap.desc}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Title Overlay Template */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300">Episode Title Template</label>
                  <input
                    type="text"
                    value={titleTemplate}
                    onChange={e => setTitleTemplate(e.target.value)}
                    placeholder="Episode {{title}} — Insights"
                    className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/[0.08] text-white text-xs focus:outline-none focus:border-purple-500 font-sans"
                  />
                </div>

                {/* Progress Bar Toggle */}
                <div className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="show_pb"
                      checked={showProgressBar}
                      onChange={e => setShowProgressBar(e.target.checked)}
                      className="rounded bg-black border-gray-700 text-purple-600 focus:ring-0"
                    />
                    <label htmlFor="show_pb" className="text-xs text-gray-300 cursor-pointer font-medium">
                      Show Animated Audio Scrubber Progress Bar
                    </label>
                  </div>
                  {showProgressBar && (
                    <input
                      type="color"
                      value={progressBarColor}
                      onChange={e => setProgressBarColor(e.target.value)}
                      className="w-6 h-6 rounded bg-transparent cursor-pointer"
                    />
                  )}
                </div>

                {/* Action Footer */}
                <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/[0.08]">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="px-4 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-gray-300 text-xs font-semibold transition-all"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-5 py-2 rounded-xl bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-400 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-purple-500/25 transition-all disabled:opacity-50"
                  >
                    {isSubmitting ? "Saving Preset..." : "Save Template Preset"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
