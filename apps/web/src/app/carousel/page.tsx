"use client";

import React, { useState } from 'react';
import { 
  Plus, 
  Trash2, 
  Copy, 
  Sparkles, 
  Download, 
  Share2, 
  Palette, 
  Type, 
  AlignLeft, 
  AlignCenter, 
  AlignRight, 
  Bold, 
  Italic, 
  Layers, 
  ChevronLeft, 
  ChevronRight,
  Sliders,
  X,
  FileUp,
  Wand2
} from 'lucide-react';
import { CarouselSlide, CarouselTheme } from '@/types';

export default function CarouselEditorPage() {
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const [activeInspectorTab, setActiveInspectorTab] = useState<'design' | 'text'>('design');
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [aiTopic, setAiTopic] = useState('');

  const [theme, setTheme] = useState<CarouselTheme>({
    background: '#0F172A',
    font_family: 'Inter',
    accent_color: '#6366F1',
    text_color: '#FFFFFF'
  });

  const [slides, setSlides] = useState<CarouselSlide[]>([
    {
      id: 's1',
      title: 'Automate Your Workflow',
      subtitle: '01 / 05',
      body: 'Stop doing repetitive manual tasks. Here is the modern content engine breakdown to 10x your output.',
      tag: 'GUIDE'
    },
    {
      id: 's2',
      title: '01. Create Once',
      subtitle: '02 / 05',
      body: 'Focus 80% of your energy on high-signal core ideas rather than platform formatting.',
      tag: 'FOUNDATION'
    },
    {
      id: 's3',
      title: '02. Aspect Ratio Transformation',
      subtitle: '03 / 05',
      body: 'Transform landscape video into 9:16 vertical clips with dynamic captions and smart reframing.',
      tag: 'MEDIA'
    },
    {
      id: 's4',
      title: '03. Native Platform Copy',
      subtitle: '04 / 05',
      body: 'Never copy-paste identical text. Adapt hooks, character constraints, and formatting for LinkedIn vs X.',
      tag: 'AI'
    },
    {
      id: 's5',
      title: '04. Distribute & Reflow',
      subtitle: '05 / 05',
      body: 'Schedule once, review live queues, and analyze cross-platform distribution seamlessly.',
      tag: 'LAUNCH'
    }
  ]);

  const currentSlide = slides[currentSlideIndex] || slides[0];

  const handleAddSlide = () => {
    const newSlide: CarouselSlide = {
      id: `s-${Date.now()}`,
      title: 'New Slide Title',
      subtitle: `0${slides.length + 1} / 0${slides.length + 1}`,
      body: 'Add your insights and takeaways here.',
      tag: 'TIP'
    };
    setSlides([...slides, newSlide]);
    setCurrentSlideIndex(slides.length);
  };

  const handleDeleteSlide = (index: number) => {
    if (slides.length <= 1) return;
    const newSlides = slides.filter((_, i) => i !== index);
    setSlides(newSlides);
    setCurrentSlideIndex(Math.max(0, index - 1));
  };

  const handleDuplicateSlide = (index: number) => {
    const slideToDup = slides[index];
    const newSlide: CarouselSlide = {
      ...slideToDup,
      id: `s-${Date.now()}`,
      title: `${slideToDup.title} (Copy)`
    };
    const newSlides = [...slides];
    newSlides.splice(index + 1, 0, newSlide);
    setSlides(newSlides);
    setCurrentSlideIndex(index + 1);
  };

  const handleAiGenerate = () => {
    if (!aiTopic.trim()) return;
    // Simulate AI generation
    const newGeneratedSlides: CarouselSlide[] = [
      { id: 'g1', title: aiTopic, subtitle: '01 / 04', body: 'The definitive blueprint for high-impact creators in 2026.', tag: 'OVERVIEW' },
      { id: 'g2', title: 'The Biggest Bottleneck', subtitle: '02 / 04', body: 'Creators waste over 15 hours a week manually re-uploading content across 6 platforms.', tag: 'PROBLEM' },
      { id: 'g3', title: 'The Unified Flow', subtitle: '03 / 04', body: 'By feeding one canonical idea into an automated pipeline, distribution velocity multiplies 5x.', tag: 'SOLUTION' },
      { id: 'g4', title: 'Start Automating Today', subtitle: '04 / 04', body: 'Download Reflow open-source or run locally with Docker in under 2 minutes.', tag: 'ACTION' },
    ];
    setSlides(newGeneratedSlides);
    setCurrentSlideIndex(0);
    setIsAiModalOpen(false);
    setAiTopic('');
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Carousel Editor</h1>
          <p className="text-xs text-gray-400 mt-0.5">Design multi-slide carousels for LinkedIn and Instagram with AI assistance.</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsAiModalOpen(true)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#161B26] hover:bg-[#1F2937] border border-[#1F2937] text-indigo-400 hover:text-indigo-300 text-xs font-semibold transition-all"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Generate Deck</span>
          </button>
          <button
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-md transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Slides (PDF / PNG)</span>
          </button>
        </div>
      </div>

      {/* 3-Column Studio: Slides Thumbnails (2 cols) | Canvas (7 cols) | Inspector (3 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Slide Thumbnails List */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">
              Slides ({slides.length})
            </span>
            <button
              onClick={handleAddSlide}
              className="p-1 rounded-lg bg-[#161B26] hover:bg-[#1F2937] text-indigo-400 hover:text-indigo-300 border border-[#1F2937]"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-2.5 max-h-[600px] overflow-y-auto pr-1">
            {slides.map((slide, idx) => (
              <div
                key={slide.id}
                onClick={() => setCurrentSlideIndex(idx)}
                className={`relative p-3 rounded-xl border cursor-pointer transition-all ${
                  currentSlideIndex === idx
                    ? 'bg-indigo-600/20 border-indigo-500 shadow-md shadow-indigo-500/10'
                    : 'bg-[#111827] border-[#1F2937] hover:border-gray-600'
                }`}
              >
                <div className="flex items-center justify-between text-[11px] text-gray-400 mb-1">
                  <span className="font-mono font-bold text-indigo-400">0{idx + 1}</span>
                  <div className="flex items-center gap-1 opacity-0 hover:opacity-100 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDuplicateSlide(idx); }}
                      className="p-1 hover:text-white"
                    >
                      <Copy className="w-3 h-3" />
                    </button>
                    {slides.length > 1 && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDeleteSlide(idx); }}
                        className="p-1 hover:text-rose-400"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                </div>
                <h4 className="text-xs font-semibold text-white truncate">{slide.title}</h4>
                <p className="text-[10px] text-gray-500 truncate mt-0.5">{slide.body}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Center: Slide Canvas (7 cols) */}
        <div className="lg:col-span-7 flex flex-col items-center justify-center bg-[#111827] border border-[#1F2937] rounded-2xl p-6 relative min-h-[550px]">
          {/* Slide Navigation Buttons */}
          <div className="w-full flex items-center justify-between mb-4 px-2">
            <button
              disabled={currentSlideIndex === 0}
              onClick={() => setCurrentSlideIndex(Math.max(0, currentSlideIndex - 1))}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-white disabled:opacity-30"
            >
              <ChevronLeft className="w-4 h-4" /> Prev
            </button>
            <span className="text-xs font-semibold text-gray-300">
              Slide {currentSlideIndex + 1} of {slides.length}
            </span>
            <button
              disabled={currentSlideIndex === slides.length - 1}
              onClick={() => setCurrentSlideIndex(Math.min(slides.length - 1, currentSlideIndex + 1))}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-white disabled:opacity-30"
            >
              Next <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {/* Interactive Slide Card */}
          <div
            className="w-full max-w-md aspect-square rounded-2xl p-8 flex flex-col justify-between shadow-2xl relative border border-white/10 transition-all overflow-hidden"
            style={{ backgroundColor: theme.background, color: theme.text_color }}
          >
            {/* Ambient Graphic / 3D Icon illustration placeholder */}
            <div className="absolute -right-8 -bottom-8 w-44 h-44 bg-gradient-to-tr from-indigo-500/20 to-purple-500/20 rounded-full blur-2xl pointer-events-none" />

            {/* Top Slide Header */}
            <div className="flex items-center justify-between z-10">
              <span className="text-xs font-bold tracking-widest px-2.5 py-1 rounded bg-white/10 uppercase">
                {currentSlide.tag || 'Reflow'}
              </span>
              <span className="text-xs font-mono opacity-60">0{currentSlideIndex + 1}</span>
            </div>

            {/* Middle Main Content */}
            <div className="space-y-4 my-auto z-10">
              <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight leading-tight">
                {currentSlide.title}
              </h2>
              <p className="text-sm opacity-80 leading-relaxed">
                {currentSlide.body}
              </p>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between pt-4 border-t border-white/10 text-[11px] opacity-60 z-10">
              <span>Reflow Engine</span>
              <span>Swipe &rarr;</span>
            </div>
          </div>
        </div>

        {/* Right: Properties Inspector (3 cols) */}
        <div className="lg:col-span-3 bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-5">
          {/* Tabs: Design / Text */}
          <div className="flex items-center gap-1 bg-[#161B26] p-1 rounded-xl border border-[#1F2937]">
            <button
              onClick={() => setActiveInspectorTab('design')}
              className={`flex-1 py-1.5 rounded-lg text-xs font-semibold text-center transition-all ${
                activeInspectorTab === 'design' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              Design
            </button>
            <button
              onClick={() => setActiveInspectorTab('text')}
              className={`flex-1 py-1.5 rounded-lg text-xs font-semibold text-center transition-all ${
                activeInspectorTab === 'text' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              Text
            </button>
          </div>

          {activeInspectorTab === 'design' ? (
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-400 block mb-2">Background Presets</label>
                <div className="grid grid-cols-4 gap-2">
                  {[
                    { bg: '#0F172A', name: 'Slate' },
                    { bg: '#18181B', name: 'Zinc' },
                    { bg: '#311042', name: 'Purple' },
                    { bg: '#0B2027', name: 'Cyan' },
                  ].map((color) => (
                    <button
                      key={color.bg}
                      onClick={() => setTheme({ ...theme, background: color.bg })}
                      className={`h-8 rounded-lg border-2 transition-all ${
                        theme.background === color.bg ? 'border-indigo-400 scale-105' : 'border-transparent'
                      }`}
                      style={{ backgroundColor: color.bg }}
                    />
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-gray-400 block mb-1">Accent Brand Color</label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={theme.accent_color}
                    onChange={(e) => setTheme({ ...theme, accent_color: e.target.value })}
                    className="w-8 h-8 rounded border-0 bg-transparent cursor-pointer"
                  />
                  <span className="text-xs font-mono text-gray-300">{theme.accent_color}</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-400 block mb-1">Slide Title</label>
                <input
                  type="text"
                  value={currentSlide.title}
                  onChange={(e) => {
                    const updated = [...slides];
                    updated[currentSlideIndex].title = e.target.value;
                    setSlides(updated);
                  }}
                  className="w-full bg-[#161B26] border border-[#1F2937] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-gray-400 block mb-1">Slide Body</label>
                <textarea
                  rows={4}
                  value={currentSlide.body}
                  onChange={(e) => {
                    const updated = [...slides];
                    updated[currentSlideIndex].body = e.target.value;
                    setSlides(updated);
                  }}
                  className="w-full bg-[#161B26] border border-[#1F2937] rounded-lg p-3 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-gray-400 block mb-1">Slide Category Tag</label>
                <input
                  type="text"
                  value={currentSlide.tag || ''}
                  onChange={(e) => {
                    const updated = [...slides];
                    updated[currentSlideIndex].tag = e.target.value;
                    setSlides(updated);
                  }}
                  className="w-full bg-[#161B26] border border-[#1F2937] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* AI Carousel Generation Modal */}
      {isAiModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-scaleUp">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Wand2 className="w-4 h-4 text-indigo-400" />
                <h3 className="text-base font-bold text-white">AI Slide Deck Generator</h3>
              </div>
              <button onClick={() => setIsAiModalOpen(false)} className="p-1 text-gray-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-gray-300 block mb-1">Topic or Article Summary</label>
                <textarea
                  rows={3}
                  value={aiTopic}
                  onChange={(e) => setAiTopic(e.target.value)}
                  placeholder="e.g. 5 Rules for Building Scalable Distributed Systems"
                  className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl p-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center justify-between text-xs text-gray-400 pt-1">
                <span>Or import text from PDF</span>
                <button className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 font-medium">
                  <FileUp className="w-3.5 h-3.5" />
                  <span>Upload PDF</span>
                </button>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#1F2937]">
              <button
                type="button"
                onClick={() => setIsAiModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-medium text-gray-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleAiGenerate}
                disabled={!aiTopic.trim()}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md disabled:opacity-50 transition-all"
              >
                Generate Deck
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
