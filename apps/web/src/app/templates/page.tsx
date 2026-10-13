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
  Maximize2
} from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { AudiogramTemplateItem } from '@/types';

const PRESET_COLORS = [
  '#6366F1', // Indigo
  '#10B981', // Emerald
  '#EC4899', // Pink
  '#F59E0B', // Amber
  '#06B6D4', // Cyan
  '#8B5CF6', // Purple
  '#EF4444', // Red
  '#FFFFFF', // White
];

const PRESET_BG_COLORS = [
  '#0F172A', // Slate 900
  '#09090B', // Zinc 950
  '#111827', // Gray 900
  '#1E1B4B', // Indigo 950
  '#064E3B', // Emerald 950
  '#172554', // Blue 950
];

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<AudiogramTemplateItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'all' | 'audiograms' | 'video'>('all');

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isPlayingAudio, setIsPlayingAudio] = useState(true);

  // Template Form State
  const [name, setName] = useState('');
  const [aspectRatio, setAspectRatio] = useState<'9:16' | '1:1' | '16:9' | '4:5'>('9:16');
  const [waveformStyle, setWaveformStyle] = useState<'BARS' | 'LINE' | 'CIRCULAR' | 'EQUALIZER' | 'WAVE'>('BARS');
  const [waveformColor, setWaveformColor] = useState('#6366F1');
  const [backgroundColor, setBackgroundColor] = useState('#0F172A');
  const [titleTemplate, setTitleTemplate] = useState('Episode {{title}}');
  const [showProgressBar, setShowProgressBar] = useState(true);
  const [progressBarColor, setProgressBarColor] = useState('#10B981');
  const [captionStyle, setCaptionStyle] = useState('BOLD_PUNCH');

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
    if (!confirm("Are you sure you want to delete this template?")) return;
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
    setBackgroundColor('#0F172A');
    setTitleTemplate('Episode {{title}}');
    setShowProgressBar(true);
    setProgressBarColor('#10B981');
    setCaptionStyle('BOLD_PUNCH');
  };

  // Live Canvas Waveform Animation
  useEffect(() => {
    if (!isModalOpen) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let step = 0;

    const render = () => {
      step += 0.05;
      const width = canvas.width;
      const height = canvas.height;

      ctx.clearRect(0, 0, width, height);

      // Draw background
      ctx.fillStyle = backgroundColor;
      ctx.fillRect(0, 0, width, height);

      // Subtle radial glow behind waveform
      const gradient = ctx.createRadialGradient(
        width / 2, height / 2, 10,
        width / 2, height / 2, width / 2
      );
      gradient.addColorStop(0, `${waveformColor}22`);
      gradient.addColorStop(1, 'transparent');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);

      // Waveform rendering
      ctx.fillStyle = waveformColor;
      ctx.strokeStyle = waveformColor;
      ctx.lineWidth = 3;

      const centerY = height / 2;

      if (waveformStyle === 'BARS' || waveformStyle === 'EQUALIZER') {
        const barCount = 28;
        const barWidth = 4;
        const spacing = (width - 60) / barCount;
        const startX = 30;

        for (let i = 0; i < barCount; i++) {
          const factor = isPlayingAudio 
            ? Math.sin(step * 2 + i * 0.4) * 0.5 + Math.cos(step * 3 + i * 0.3) * 0.5 
            : 0.1;
          const barHeight = Math.max(6, Math.abs(factor) * (height * 0.28));
          const x = startX + i * spacing;
          const y = centerY - barHeight / 2;

          ctx.beginPath();
          ctx.roundRect(x, y, barWidth, barHeight, 3);
          ctx.fill();
        }
      } else if (waveformStyle === 'LINE' || waveformStyle === 'WAVE') {
        ctx.beginPath();
        for (let x = 20; x < width - 20; x += 4) {
          const factor = isPlayingAudio 
            ? Math.sin((x / 20) + step * 2) * Math.cos((x / 40) + step) 
            : 0.05;
          const y = centerY + factor * (height * 0.16);
          if (x === 20) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      } else if (waveformStyle === 'CIRCULAR') {
        const radius = Math.min(width, height) * 0.18;
        const points = 32;

        ctx.beginPath();
        for (let i = 0; i <= points; i++) {
          const angle = (i / points) * Math.PI * 2;
          const factor = isPlayingAudio 
            ? Math.sin(step * 3 + i * 0.8) * 12 
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

      // Title Template Simulation
      ctx.fillStyle = '#FFFFFF';
      ctx.font = 'bold 12px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(titleTemplate.replace('{{title}}', 'Exclusive Masterclass'), width / 2, centerY - 65);

      // Subtitle Simulation
      ctx.fillStyle = '#94A3B8';
      ctx.font = '9px Inter, sans-serif';
      ctx.fillText('"Every great strategy starts with focus..."', width / 2, centerY + 65);

      // Progress Bar Simulation
      if (showProgressBar) {
        const barY = height - 25;
        ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.fillRect(25, barY, width - 50, 4);

        ctx.fillStyle = progressBarColor;
        const progressWidth = ((Math.sin(step * 0.4) + 1) / 2) * (width - 50);
        ctx.fillRect(25, barY, progressWidth, 4);
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
    aspectRatio
  ]);

  const filteredTemplates = templates.filter(t => {
    if (activeTab === 'audiograms') return true;
    if (activeTab === 'video') return t.aspect_ratio === '9:16' || t.aspect_ratio === '16:9';
    return true;
  });

  return (
    <div className="space-y-6 animate-fadeIn pb-16">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-purple-500/20 to-pink-500/20 border border-purple-500/30">
              <LayoutTemplate className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Repurpose Templates Studio</h1>
              <p className="text-xs text-gray-400 mt-0.5">
                Design and manage reusable Audiogram soundwaves, video framing, and captions for your automated pipelines.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadTemplates}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-[#161B26] hover:bg-[#1F2937] border border-[#1F2937] text-gray-300 text-xs font-medium transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-purple-500/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Create Template</span>
          </button>
        </div>
      </div>

      {/* Tabs Filter */}
      <div className="flex items-center justify-between border-b border-[#1F2937] pb-3">
        <div className="flex items-center gap-2">
          {(['all', 'audiograms', 'video'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                activeTab === tab
                  ? 'bg-purple-600/20 text-purple-400 border border-purple-500/30'
                  : 'text-gray-400 hover:text-white hover:bg-[#161B26]'
              }`}
            >
              {tab === 'all' && 'All Templates'}
              {tab === 'audiograms' && 'Audiograms (Soundwave)'}
              {tab === 'video' && 'Video Framing'}
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

      {/* Templates Grid */}
      {filteredTemplates.length === 0 ? (
        <div className="text-center py-16 bg-[#111827] border border-[#1F2937] rounded-3xl p-8 space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center mx-auto text-purple-400">
            <LayoutTemplate className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">No custom templates saved yet</h3>
            <p className="text-xs text-gray-400 max-w-md mx-auto mt-1">
              Create custom Audiogram templates with customized waveforms, brand colors, and aspect ratios to match your show.
            </p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-md transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Create First Template</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredTemplates.map(tmpl => (
            <div
              key={tmpl.id}
              className="bg-[#111827] border border-[#1F2937] rounded-2xl p-4 hover:border-gray-700 transition-all flex flex-col justify-between space-y-4 shadow-sm group"
            >
              {/* Visual Card Banner */}
              <div 
                className="w-full h-44 rounded-xl flex flex-col items-center justify-center relative overflow-hidden border border-[#1F2937]"
                style={{ backgroundColor: tmpl.background_color || '#0F172A' }}
              >
                {/* Simulated Waveform Preview */}
                <div className="flex items-center justify-center gap-1.5 h-16 w-3/4">
                  {[18, 36, 24, 48, 62, 34, 52, 28, 44, 20, 56, 30].map((h, i) => (
                    <div
                      key={i}
                      className="w-1.5 rounded-full transition-all"
                      style={{
                        height: `${h}%`,
                        backgroundColor: tmpl.waveform_color || '#6366F1'
                      }}
                    />
                  ))}
                </div>

                {/* Title badge in card */}
                <div className="absolute top-3 inset-x-3 text-center">
                  <span className="text-[11px] font-bold text-white/90 truncate block px-2">
                    {tmpl.title_template || tmpl.name}
                  </span>
                </div>

                {/* Aspect ratio badge */}
                <div className="absolute bottom-3 left-3 flex items-center gap-1.5 bg-black/60 backdrop-blur-md px-2 py-0.5 rounded-md border border-white/10 text-[10px] text-gray-300 font-semibold">
                  <Maximize2 className="w-3 h-3 text-purple-400" />
                  <span>{tmpl.aspect_ratio}</span>
                </div>

                {/* Style badge */}
                <div className="absolute bottom-3 right-3 bg-black/60 backdrop-blur-md px-2 py-0.5 rounded-md border border-white/10 text-[10px] text-gray-300 font-semibold">
                  <span>{tmpl.waveform_style}</span>
                </div>
              </div>

              {/* Template Info & Actions */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-white tracking-tight">{tmpl.name}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="w-2.5 h-2.5 rounded-full border border-white/20" style={{ backgroundColor: tmpl.waveform_color }} />
                      <span className="text-[11px] text-gray-400">Wave Color</span>
                      <span className="text-gray-600">•</span>
                      <span className="text-[11px] text-gray-400 capitalize">{tmpl.caption_style.toLowerCase().replace('_', ' ')}</span>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDeleteTemplate(tmpl.id)}
                    className="p-1.5 rounded-xl text-gray-400 hover:text-red-400 hover:bg-[#161B26] transition-all opacity-0 group-hover:opacity-100"
                    title="Delete template"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-[#1F2937]/80 text-xs">
                  <Link
                    href={`/workflows`}
                    className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                  >
                    <span>Attach to Workflow</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>

                  <span className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">
                    Preset Ready
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create / Edit Template Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="bg-[#111827] border border-[#1F2937] rounded-3xl w-full max-w-4xl max-h-[92vh] overflow-y-auto p-6 space-y-6 shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-[#1F2937] pb-4">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-purple-500/20 border border-purple-500/30 text-purple-400">
                  <Palette className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Audiogram Template Designer</h3>
                  <p className="text-xs text-gray-400">Configure real-time waveform visualizers, aspect ratios, and typography.</p>
                </div>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1.5 rounded-xl text-gray-400 hover:text-white hover:bg-[#161B26]"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Designer Layout: Left Live Canvas Preview, Right Settings */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Live Canvas Preview (5 cols) */}
              <div className="lg:col-span-5 flex flex-col items-center justify-center bg-[#0B0F17] border border-[#1F2937] rounded-2xl p-4 space-y-3">
                <div className="flex items-center justify-between w-full px-1">
                  <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Eye className="w-3.5 h-3.5 text-purple-400" />
                    Live Canvas Preview
                  </span>
                  <button
                    onClick={() => setIsPlayingAudio(!isPlayingAudio)}
                    className="flex items-center gap-1 px-2 py-1 rounded-lg bg-[#161B26] border border-[#1F2937] text-gray-300 text-[10px] font-semibold hover:text-white"
                  >
                    {isPlayingAudio ? (
                      <>
                        <Pause className="w-3 h-3 text-amber-400" />
                        <span>Pause Wave</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3 h-3 text-emerald-400" />
                        <span>Play Wave</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Aspect ratio frame container */}
                <div className="flex items-center justify-center w-full min-h-[340px]">
                  <canvas
                    ref={canvasRef}
                    width={aspectRatio === '9:16' ? 220 : aspectRatio === '1:1' ? 300 : 340}
                    height={aspectRatio === '9:16' ? 360 : aspectRatio === '1:1' ? 300 : 200}
                    className="rounded-xl shadow-2xl border border-white/10 transition-all max-h-[380px]"
                  />
                </div>

                <div className="text-[10px] text-gray-500 text-center">
                  Simulated 48kHz audio waveform rendering at 60 FPS
                </div>
              </div>

              {/* Right Settings Controls (7 cols) */}
              <form onSubmit={handleCreateTemplate} className="lg:col-span-7 space-y-4">
                {/* Template Name */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300">Template Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Neon Cyberpunk Vertical (9:16)"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-[#161B26] border border-[#1F2937] text-white text-xs focus:outline-none focus:border-purple-500"
                  />
                </div>

                {/* Aspect Ratio Selector */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300">Target Canvas Aspect Ratio</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { id: '9:16', label: '9:16 Vertical', sub: 'Shorts & Reels' },
                      { id: '1:1', label: '1:1 Square', sub: 'Feed Posts' },
                      { id: '16:9', label: '16:9 Landscape', sub: 'YouTube' }
                    ].map(ar => (
                      <button
                        type="button"
                        key={ar.id}
                        onClick={() => setAspectRatio(ar.id as any)}
                        className={`p-2 rounded-xl border text-center transition-all ${
                          aspectRatio === ar.id
                            ? 'bg-purple-600/20 border-purple-500 text-white font-semibold'
                            : 'bg-[#161B26] border-[#1F2937] text-gray-400 hover:text-white'
                        }`}
                      >
                        <div className="text-xs font-bold">{ar.label}</div>
                        <div className="text-[10px] text-gray-400">{ar.sub}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Soundwave Visualizer Style */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300">Soundwave Style</label>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {[
                      { id: 'BARS', label: 'Equalizer Bars' },
                      { id: 'LINE', label: 'Oscilloscope' },
                      { id: 'CIRCULAR', label: 'Circular Ring' },
                      { id: 'WAVE', label: 'Smooth Wave' }
                    ].map(style => (
                      <button
                        type="button"
                        key={style.id}
                        onClick={() => setWaveformStyle(style.id as any)}
                        className={`px-3 py-2 rounded-xl border text-xs font-medium text-center transition-all ${
                          waveformStyle === style.id
                            ? 'bg-purple-600/20 border-purple-500 text-white font-semibold'
                            : 'bg-[#161B26] border-[#1F2937] text-gray-400 hover:text-white'
                        }`}
                      >
                        {style.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Waveform Color Palette */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300">Waveform Color</label>
                  <div className="flex items-center gap-2">
                    {PRESET_COLORS.map(c => (
                      <button
                        type="button"
                        key={c}
                        onClick={() => setWaveformColor(c)}
                        className={`w-6 h-6 rounded-full border transition-all ${
                          waveformColor === c ? 'ring-2 ring-purple-400 scale-110' : 'border-white/20'
                        }`}
                        style={{ backgroundColor: c }}
                      />
                    ))}
                    <input
                      type="color"
                      value={waveformColor}
                      onChange={e => setWaveformColor(e.target.value)}
                      className="w-7 h-7 rounded-lg bg-transparent cursor-pointer ml-2"
                    />
                  </div>
                </div>

                {/* Background Color Palette */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300">Canvas Background Color</label>
                  <div className="flex items-center gap-2">
                    {PRESET_BG_COLORS.map(bg => (
                      <button
                        type="button"
                        key={bg}
                        onClick={() => setBackgroundColor(bg)}
                        className={`w-6 h-6 rounded-full border transition-all ${
                          backgroundColor === bg ? 'ring-2 ring-purple-400 scale-110' : 'border-white/20'
                        }`}
                        style={{ backgroundColor: bg }}
                      />
                    ))}
                    <input
                      type="color"
                      value={backgroundColor}
                      onChange={e => setBackgroundColor(e.target.value)}
                      className="w-7 h-7 rounded-lg bg-transparent cursor-pointer ml-2"
                    />
                  </div>
                </div>

                {/* Title Template */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300">Title Header Overlay</label>
                  <input
                    type="text"
                    value={titleTemplate}
                    onChange={e => setTitleTemplate(e.target.value)}
                    placeholder="e.g. {{title}} - Host Name"
                    className="w-full px-3 py-2 rounded-xl bg-[#161B26] border border-[#1F2937] text-white text-xs focus:outline-none focus:border-purple-500"
                  />
                </div>

                {/* Progress Bar & Captions */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  <div className="flex items-center gap-2 p-2.5 rounded-xl bg-[#161B26] border border-[#1F2937]">
                    <input
                      type="checkbox"
                      id="show_pb"
                      checked={showProgressBar}
                      onChange={e => setShowProgressBar(e.target.checked)}
                      className="rounded bg-[#111827] border-gray-700 text-purple-600 focus:ring-0"
                    />
                    <label htmlFor="show_pb" className="text-xs text-gray-300 cursor-pointer">
                      Show Animated Audio Progress Bar
                    </label>
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] text-gray-400">Caption Style</label>
                    <select
                      value={captionStyle}
                      onChange={e => setCaptionStyle(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-[#161B26] border border-[#1F2937] text-white text-xs"
                    >
                      <option value="BOLD_PUNCH">Bold Punch (Alex Hormozi)</option>
                      <option value="CLEAN_SUB">Clean Subtitles (Minimal)</option>
                      <option value="NEON_GLOW">Neon Glow (Dynamic)</option>
                    </select>
                  </div>
                </div>

                {/* Footer Buttons */}
                <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#1F2937]">
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
                    className="px-5 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-purple-500/20 transition-all disabled:opacity-50"
                  >
                    {isSubmitting ? "Saving..." : "Save Template Preset"}
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
