"use client";

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { 
  Plus, 
  Trash2, 
  Copy, 
  Sparkles, 
  Download, 
  Palette, 
  Type, 
  ChevronLeft, 
  ChevronRight,
  ArrowUp,
  ArrowDown,
  X,
  FileUp,
  Wand2,
  RefreshCw,
  CheckCircle2,
  FileText,
  Save,
  Layers,
  ExternalLink
} from 'lucide-react';
import { CarouselItem, CarouselSlideItem, ContentItem } from '@/types';
import { api } from '@/lib/api';

const TEMPLATE_STYLES: Record<string, { bg: string; text: string; accent: string; muted: string; name: string }> = {
  MINIMAL: { bg: '#0F172A', text: '#FFFFFF', accent: '#6366F1', muted: '#94A3B8', name: 'Minimal Slate' },
  EDITORIAL: { bg: '#18181B', text: '#F8FAFC', accent: '#F59E0B', muted: '#A1A1AA', name: 'Editorial Zinc' },
  BOLD: { bg: '#1E1B4B', text: '#FFFFFF', accent: '#06B6D4', muted: '#C4B5FD', name: 'Bold Midnight' },
  EDUCATIONAL: { bg: '#0B2027', text: '#F1F5F9', accent: '#10B981', muted: '#94A3B8', name: 'Educational Teal' }
};

function CarouselEditor() {
  const searchParams = useSearchParams();
  const urlCarouselId = searchParams.get('id');

  const [carouselList, setCarouselList] = useState<CarouselItem[]>([]);
  const [activeCarousel, setActiveCarousel] = useState<CarouselItem | null>(null);
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const [activeInspectorTab, setActiveInspectorTab] = useState<'design' | 'text'>('text');
  
  // AI Modal State
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [contentList, setContentList] = useState<ContentItem[]>([]);
  const [selectedContentId, setSelectedContentId] = useState<string>('');
  const [targetSlideCount, setTargetSlideCount] = useState<number>(5);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('MINIMAL');
  const [customPrompt, setCustomPrompt] = useState<string>('');
  
  // Loading & Feedback
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);
  const [exportModalOpen, setExportModalOpen] = useState(false);

  useEffect(() => {
    loadCarousels(urlCarouselId);
    loadSourceContents();
  }, [urlCarouselId]);

  const loadSourceContents = async () => {
    try {
      const res = await api.getContentList({ limit: 50 });
      setContentList(res.items || []);
    } catch {}
  };

  const loadCarousels = async (preferredId?: string | null) => {
    try {
      const res = await api.getCarousels();
      const items = res.items || [];
      setCarouselList(items);

      if (items.length > 0) {
        const found = preferredId ? items.find(c => c.id === preferredId) : items[0];
        const target = found || items[0];
        const fullCarousel = await api.getCarousel(target.id);
        setActiveCarousel(fullCarousel);
      } else {
        // Create initial default carousel if empty
        const initial = await api.createCarousel("My First Content Carousel", "MINIMAL");
        await api.addSlide(initial.id, "Automate Your Workflow", "Focus 80% of your energy on high-signal core ideas.", "GUIDE");
        await api.addSlide(initial.id, "Aspect Ratio Conversion", "Transform landscape video into 9:16 vertical clips.", "MEDIA");
        await api.addSlide(initial.id, "Native Platform Copies", "Adapt hooks and constraints for LinkedIn vs X.", "AI");
        const fresh = await api.getCarousel(initial.id);
        setActiveCarousel(fresh);
        setCarouselList([fresh]);
      }
    } catch (e) {
      console.warn("Failed to load carousels:", e);
    }
  };

  const slides = activeCarousel?.slides || [];
  const currentSlide: CarouselSlideItem | undefined = slides[currentSlideIndex] || slides[0];
  const currentTemplateKey = activeCarousel?.template?.toUpperCase() || 'MINIMAL';
  const currentTheme = TEMPLATE_STYLES[currentTemplateKey] || TEMPLATE_STYLES.MINIMAL;

  const handleCreateNewDeck = async () => {
    try {
      const title = prompt("Enter Deck Title:", "New Social Carousel") || "New Social Carousel";
      const created = await api.createCarousel(title, selectedTemplate);
      await api.addSlide(created.id, "Catchy Headline", "Add your high-signal takeaway here.", "TIP");
      const fresh = await api.getCarousel(created.id);
      setActiveCarousel(fresh);
      setCarouselList([fresh, ...carouselList]);
      setCurrentSlideIndex(0);
      setNotification(`Created new deck: ${fresh.title}`);
    } catch (e: any) {
      setNotification(`Failed to create deck: ${e.message}`);
    }
  };

  const handleAddSlide = async () => {
    if (!activeCarousel) return;
    try {
      const updated = await api.addSlide(
        activeCarousel.id,
        "New Slide Title",
        "Add key points and insights here.",
        "INSIGHT"
      );
      setActiveCarousel(updated);
      setCurrentSlideIndex(updated.slides.length - 1);
    } catch (e: any) {
      setNotification(`Add slide error: ${e.message}`);
    }
  };

  const handleDeleteSlide = async (slideId: string, index: number) => {
    if (!activeCarousel || slides.length <= 1) return;
    try {
      const updated = await api.deleteSlide(activeCarousel.id, slideId);
      setActiveCarousel(updated);
      setCurrentSlideIndex(Math.max(0, index - 1));
    } catch (e: any) {
      setNotification(`Delete error: ${e.message}`);
    }
  };

  const handleDuplicateSlide = async (slide: CarouselSlideItem) => {
    if (!activeCarousel) return;
    try {
      const updated = await api.addSlide(
        activeCarousel.id,
        `${slide.headline} (Copy)`,
        slide.body,
        slide.tag || "INSIGHT"
      );
      setActiveCarousel(updated);
      setCurrentSlideIndex(updated.slides.length - 1);
    } catch (e: any) {
      setNotification(`Duplicate error: ${e.message}`);
    }
  };

  const handleMoveSlide = async (index: number, direction: 'up' | 'down') => {
    if (!activeCarousel) return;
    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= slides.length) return;

    const newSlideOrder = [...slides];
    const temp = newSlideOrder[index];
    newSlideOrder[index] = newSlideOrder[targetIdx];
    newSlideOrder[targetIdx] = temp;

    try {
      const updated = await api.reorderSlides(activeCarousel.id, newSlideOrder.map(s => s.id));
      setActiveCarousel(updated);
      setCurrentSlideIndex(targetIdx);
    } catch (e: any) {
      setNotification(`Reorder error: ${e.message}`);
    }
  };

  const handleSaveSlideChanges = async (field: 'headline' | 'body' | 'tag', value: string) => {
    if (!activeCarousel || !currentSlide) return;
    setIsSaving(true);
    try {
      const updated = await api.updateSlide(activeCarousel.id, currentSlide.id, {
        [field]: value
      });
      setActiveCarousel(updated);
    } catch (e: any) {
      setNotification(`Save error: ${e.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleChangeTemplate = async (templateKey: string) => {
    if (!activeCarousel) return;
    try {
      const updated = await api.updateCarousel(activeCarousel.id, { template: templateKey });
      setActiveCarousel(updated);
      setNotification(`Switched template to ${TEMPLATE_STYLES[templateKey].name}`);
    } catch (e: any) {
      setNotification(`Template update error: ${e.message}`);
    }
  };

  const handleGenerateAI = async () => {
    if (!activeCarousel) return;
    setIsGenerating(true);
    setNotification(null);
    try {
      await api.generateCarouselAI(
        activeCarousel.id,
        targetSlideCount,
        selectedTemplate,
        customPrompt || undefined
      );
      setNotification("AI generation queued! Loading synthesized slides...");
      setIsAiModalOpen(false);

      // Poll for completion
      setTimeout(async () => {
        const fresh = await api.getCarousel(activeCarousel.id);
        setActiveCarousel(fresh);
        setCurrentSlideIndex(0);
        setIsGenerating(false);
        setNotification(`Deck '${fresh.title}' generated with ${fresh.slides.length} slides!`);
      }, 1500);
    } catch (e: any) {
      setNotification(`Generation failed: ${e.message}`);
      setIsGenerating(false);
    }
  };

  const handleRenderAndExport = async () => {
    if (!activeCarousel) return;
    setIsRendering(true);
    try {
      await api.renderCarousel(activeCarousel.id);
      const fresh = await api.getCarousel(activeCarousel.id);
      setActiveCarousel(fresh);
      setExportModalOpen(true);
    } catch (e: any) {
      setNotification(`Render failed: ${e.message}`);
    } finally {
      setIsRendering(false);
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Top Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">
              {activeCarousel ? activeCarousel.title : "Carousel Studio"}
            </h1>
            {activeCarousel && (
              <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded font-mono border border-indigo-500/30">
                v{activeCarousel.version}
              </span>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            Design, plan with AI, and export multi-slide carousel decks (1080x1080) for LinkedIn and Instagram.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleCreateNewDeck}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#161B26] hover:bg-[#1F2937] border border-[#1F2937] text-gray-300 hover:text-white text-xs font-semibold transition-all"
          >
            <Plus className="w-3.5 h-3.5 text-indigo-400" />
            <span>New Deck</span>
          </button>
          <button
            onClick={() => setIsAiModalOpen(true)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#161B26] hover:bg-[#1F2937] border border-[#1F2937] text-indigo-400 hover:text-indigo-300 text-xs font-semibold transition-all"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Generate Deck</span>
          </button>
          <button
            onClick={handleRenderAndExport}
            disabled={isRendering || !slides.length}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-md transition-all disabled:opacity-50"
          >
            {isRendering ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
            <span>{isRendering ? "Rendering..." : "Export (PDF / PNG)"}</span>
          </button>
        </div>
      </div>

      {notification && (
        <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-xl p-3 text-xs text-indigo-300 flex items-center justify-between animate-fadeIn">
          <span>{notification}</span>
          <button onClick={() => setNotification(null)} className="text-gray-400 hover:text-white font-semibold">✕</button>
        </div>
      )}

      {/* 3-Column Studio Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (3 cols): Slide Deck Thumbnails */}
        <div className="lg:col-span-3 space-y-3">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">
              Slides ({slides.length})
            </span>
            <button
              onClick={handleAddSlide}
              className="flex items-center gap-1 px-2 py-1 rounded-lg bg-[#161B26] hover:bg-[#1F2937] text-indigo-400 hover:text-indigo-300 border border-[#1F2937] text-xs font-semibold"
            >
              <Plus className="w-3 h-3" />
              <span>Add</span>
            </button>
          </div>

          <div className="space-y-2.5 max-h-[620px] overflow-y-auto pr-1">
            {slides.map((slide, idx) => {
              const isSelected = currentSlideIndex === idx;
              return (
                <div
                  key={slide.id}
                  onClick={() => setCurrentSlideIndex(idx)}
                  className={`group relative p-3 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-indigo-600/20 border-indigo-500 shadow-md shadow-indigo-500/10'
                      : 'bg-[#111827] border-[#1F2937] hover:border-gray-600'
                  }`}
                >
                  <div className="flex items-center justify-between text-[11px] text-gray-400 mb-1">
                    <span className="font-mono font-bold text-indigo-400">
                      {idx + 1 < 10 ? `0${idx + 1}` : idx + 1}
                    </span>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {idx > 0 && (
                        <button
                          onClick={(e) => { e.stopPropagation(); handleMoveSlide(idx, 'up'); }}
                          className="p-0.5 hover:text-white"
                          title="Move Up"
                        >
                          <ArrowUp className="w-3 h-3" />
                        </button>
                      )}
                      {idx < slides.length - 1 && (
                        <button
                          onClick={(e) => { e.stopPropagation(); handleMoveSlide(idx, 'down'); }}
                          className="p-0.5 hover:text-white"
                          title="Move Down"
                        >
                          <ArrowDown className="w-3 h-3" />
                        </button>
                      )}
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDuplicateSlide(slide); }}
                        className="p-0.5 hover:text-white"
                        title="Duplicate"
                      >
                        <Copy className="w-3 h-3" />
                      </button>
                      {slides.length > 1 && (
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDeleteSlide(slide.id, idx); }}
                          className="p-0.5 hover:text-rose-400"
                          title="Delete"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  </div>
                  <h4 className="text-xs font-semibold text-white truncate">{slide.headline || 'Untitled Slide'}</h4>
                  <p className="text-[10px] text-gray-500 truncate mt-0.5">{slide.body}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Center Column (6 cols): Live Pixel-Perfect Slide Canvas */}
        <div className="lg:col-span-6 flex flex-col items-center justify-center bg-[#111827] border border-[#1F2937] rounded-2xl p-6 relative min-h-[550px]">
          {/* Navigation Bar */}
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

          {/* 1080x1080 Aspect-Ratio Slide Card */}
          {currentSlide ? (
            <div
              className="w-full max-w-md aspect-square rounded-2xl p-8 flex flex-col justify-between shadow-2xl relative border border-white/10 transition-all overflow-hidden"
              style={{ backgroundColor: currentTheme.bg, color: currentTheme.text }}
            >
              {/* Background ambient glow */}
              <div 
                className="absolute -right-8 -bottom-8 w-44 h-44 rounded-full blur-3xl pointer-events-none opacity-20"
                style={{ backgroundColor: currentTheme.accent }}
              />

              {/* Header Badge */}
              <div className="flex items-center justify-between z-10">
                <span 
                  className="text-xs font-bold tracking-widest px-2.5 py-1 rounded uppercase font-mono"
                  style={{ backgroundColor: currentTheme.accent, color: '#FFFFFF' }}
                >
                  {currentSlide.tag || 'INSIGHT'}
                </span>
                <span className="text-xs font-mono" style={{ color: currentTheme.muted }}>
                  {currentSlideIndex + 1 < 10 ? `0${currentSlideIndex + 1}` : currentSlideIndex + 1} / {slides.length < 10 ? `0${slides.length}` : slides.length}
                </span>
              </div>

              {/* Center Content */}
              <div className="space-y-4 my-auto z-10">
                <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight leading-tight">
                  {currentSlide.headline}
                </h2>
                <p 
                  className="text-sm leading-relaxed whitespace-pre-line"
                  style={{ color: currentTheme.muted }}
                >
                  {currentSlide.body}
                </p>
              </div>

              {/* Footer */}
              <div 
                className="flex items-center justify-between pt-4 border-t text-[11px] font-mono z-10"
                style={{ borderColor: 'rgba(255,255,255,0.1)', color: currentTheme.muted }}
              >
                <span>Reflow Engine</span>
                <span>Swipe &rarr;</span>
              </div>
            </div>
          ) : (
            <div className="text-xs text-gray-500">No slides in this deck. Add a slide to begin.</div>
          )}
        </div>

        {/* Right Column (3 cols): Properties Inspector & Live Editor */}
        <div className="lg:col-span-3 bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-5">
          <div className="flex items-center gap-1 bg-[#161B26] p-1 rounded-xl border border-[#1F2937]">
            <button
              onClick={() => setActiveInspectorTab('text')}
              className={`flex-1 py-1.5 rounded-lg text-xs font-semibold text-center transition-all ${
                activeInspectorTab === 'text' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              Text
            </button>
            <button
              onClick={() => setActiveInspectorTab('design')}
              className={`flex-1 py-1.5 rounded-lg text-xs font-semibold text-center transition-all ${
                activeInspectorTab === 'design' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              Templates
            </button>
          </div>

          {activeInspectorTab === 'text' && currentSlide ? (
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-400 block mb-1">Slide Headline</label>
                <input
                  type="text"
                  value={currentSlide.headline}
                  onChange={(e) => {
                    const val = e.target.value;
                    const copy = [...slides];
                    copy[currentSlideIndex].headline = val;
                    setActiveCarousel({ ...activeCarousel!, slides: copy });
                  }}
                  onBlur={(e) => handleSaveSlideChanges('headline', e.target.value)}
                  className="w-full bg-[#161B26] border border-[#1F2937] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-gray-400 block mb-1">Slide Body</label>
                <textarea
                  rows={5}
                  value={currentSlide.body}
                  onChange={(e) => {
                    const val = e.target.value;
                    const copy = [...slides];
                    copy[currentSlideIndex].body = val;
                    setActiveCarousel({ ...activeCarousel!, slides: copy });
                  }}
                  onBlur={(e) => handleSaveSlideChanges('body', e.target.value)}
                  className="w-full bg-[#161B26] border border-[#1F2937] rounded-lg p-3 text-xs text-white focus:outline-none focus:border-indigo-500 leading-relaxed"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-gray-400 block mb-1">Category Tag / Pill</label>
                <input
                  type="text"
                  value={currentSlide.tag || ''}
                  onChange={(e) => {
                    const val = e.target.value;
                    const copy = [...slides];
                    copy[currentSlideIndex].tag = val;
                    setActiveCarousel({ ...activeCarousel!, slides: copy });
                  }}
                  onBlur={(e) => handleSaveSlideChanges('tag', e.target.value)}
                  className="w-full bg-[#161B26] border border-[#1F2937] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-2 text-[11px] text-gray-500 font-mono flex items-center gap-1">
                <Save className="w-3.5 h-3.5 text-emerald-400" />
                <span>{isSaving ? "Saving..." : "Auto-saved to database"}</span>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-400 block mb-2">Design Templates</label>
                <div className="space-y-2">
                  {Object.entries(TEMPLATE_STYLES).map(([key, style]) => {
                    const isCurrent = currentTemplateKey === key;
                    return (
                      <button
                        key={key}
                        onClick={() => handleChangeTemplate(key)}
                        className={`w-full p-3 rounded-xl border text-left flex items-center justify-between transition-all ${
                          isCurrent
                            ? 'border-indigo-500 bg-indigo-600/10 shadow-sm'
                            : 'border-[#1F2937] bg-[#161B26] hover:border-gray-600'
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <div 
                            className="w-5 h-5 rounded-md border border-white/20"
                            style={{ backgroundColor: style.bg }}
                          />
                          <div>
                            <span className="text-xs font-bold text-white block">{style.name}</span>
                            <span className="text-[10px] text-gray-400 font-mono">1080 x 1080 px</span>
                          </div>
                        </div>
                        {isCurrent && <CheckCircle2 className="w-4 h-4 text-indigo-400" />}
                      </button>
                    );
                  })}
                </div>
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
                <h3 className="text-base font-bold text-white">AI Carousel Planner</h3>
              </div>
              <button onClick={() => setIsAiModalOpen(false)} className="p-1 text-gray-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3.5">
              <div>
                <label className="text-xs font-medium text-gray-300 block mb-1">Source Content Asset (Optional)</label>
                <select
                  value={selectedContentId}
                  onChange={(e) => setSelectedContentId(e.target.value)}
                  className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">None (Use prompt below)</option>
                  {contentList.map((c) => (
                    <option key={c.id} value={c.id}>
                      [{c.content_type}] {c.title}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-gray-300 block mb-1">Custom Instructions / Topic</label>
                <textarea
                  rows={3}
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  placeholder="e.g. Focus on practical backend architecture tradeoffs and scaling takeaways"
                  className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl p-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-300 block mb-1">Slide Count</label>
                  <select
                    value={targetSlideCount}
                    onChange={(e) => setTargetSlideCount(Number(e.target.value))}
                    className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl p-2 text-xs text-white focus:outline-none"
                  >
                    {[4, 5, 6, 7, 8, 10, 12].map(n => (
                      <option key={n} value={n}>{n} Slides</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-300 block mb-1">Template Style</label>
                  <select
                    value={selectedTemplate}
                    onChange={(e) => setSelectedTemplate(e.target.value)}
                    className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl p-2 text-xs text-white focus:outline-none"
                  >
                    {Object.entries(TEMPLATE_STYLES).map(([k, s]) => (
                      <option key={k} value={k}>{s.name}</option>
                    ))}
                  </select>
                </div>
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
                onClick={handleGenerateAI}
                disabled={isGenerating}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md disabled:opacity-50 transition-all"
              >
                {isGenerating ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                <span>{isGenerating ? "Planning..." : "Generate Deck"}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Export & Download Modal */}
      {exportModalOpen && activeCarousel && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-scaleUp">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Download className="w-4 h-4 text-emerald-400" />
                <h3 className="text-base font-bold text-white">Carousel Exports Ready</h3>
              </div>
              <button onClick={() => setExportModalOpen(false)} className="p-1 text-gray-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-gray-300">
              The carousel has been rendered into high-resolution 1080x1080 PNG slides and compiled into a single multi-page PDF document.
            </p>

            <div className="space-y-2.5 pt-2">
              {activeCarousel.exports?.map((exp) => (
                <div key={exp.id} className="p-3 bg-[#161B26] rounded-xl border border-[#1F2937] flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <FileText className={`w-5 h-5 ${exp.format === 'PDF' ? 'text-red-400' : 'text-cyan-400'}`} />
                    <div>
                      <span className="text-xs font-bold text-white block">
                        {exp.format === 'PDF' ? `Multi-Page Document (${activeCarousel.slides.length} Slides)` : 'High-Res Slide PNG'}
                      </span>
                      <span className="text-[10px] text-gray-500 font-mono">
                        {exp.format} • {(exp.file_size / 1024).toFixed(1)} KB
                      </span>
                    </div>
                  </div>
                  <a
                    href={api.getExportDownloadUrl(activeCarousel.id, exp.id)}
                    target="_blank"
                    rel="noreferrer"
                    download
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all shadow-sm"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download</span>
                  </a>
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-3 border-t border-[#1F2937]">
              <button
                onClick={() => setExportModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-[#161B26] hover:bg-[#1F2937] text-gray-300 hover:text-white text-xs font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function CarouselStudioPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs text-gray-500">Loading Carousel Studio...</div>}>
      <CarouselEditor />
    </Suspense>
  );
}
