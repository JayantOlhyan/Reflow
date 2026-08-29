"use client";

import React, { useState } from 'react';
import { 
  Sparkles, 
  Play, 
  Pause, 
  Volume2, 
  Maximize2, 
  Check, 
  Scissors, 
  Type, 
  Hash, 
  Subtitles, 
  FileText, 
  Send, 
  Clock, 
  Copy, 
  CheckCheck,
  RefreshCw,
  Sliders
} from 'lucide-react';
import { YoutubeIcon, InstagramIcon, TiktokIcon, LinkedinIcon, XIcon, FacebookIcon } from '@/components/ui/SocialIcons';

export default function RepurposeEditorPage() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState('9:16');
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeOutputTab, setActiveOutputTab] = useState('instagram');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const [destinations, setDestinations] = useState({
    youtube: true,
    instagram: true,
    tiktok: true,
    linkedin: true,
    x: true,
    facebook: false
  });

  const [aiOptions, setAiOptions] = useState({
    caption: true,
    title: true,
    description: true,
    hashtags: true,
    subtitles: true,
    findClips: true
  });

  const formats = [
    { id: '16:9', label: 'Original (16:9)', aspect: 'aspect-video' },
    { id: '9:16', label: 'Vertical (9:16)', aspect: 'aspect-[9/16]' },
    { id: '1:1', label: 'Square (1:1)', aspect: 'aspect-square' },
    { id: '4:5', label: 'Portrait (4:5)', aspect: 'aspect-[4/5]' },
  ];

  const [generatedOutputs, setGeneratedOutputs] = useState({
    instagram: {
      title: "Building an AI SaaS in 24 Hours 🚀",
      caption: "Stop spending 3 months validating an idea that takes 24 hours to test. Here is the exact stack I used to build and deploy an AI app in one day 👇\n\n1. Next.js 14 + Tailwind for blazing speed\n2. FastAPI backend with async streaming\n3. Gemini 1.5 Pro for content synthesis\n\nWhat are you building this weekend? Drop it in the comments! 👇",
      hashtags: "#buildinpublic #solopreneur #aiagent #softwareengineer #saas #developers",
      format: "9:16 Reel"
    },
    linkedin: {
      title: "How I built an AI SaaS in 24 hours (and what it taught me about modern dev velocity)",
      caption: "In 2026, building software isn't about writing boilerplate. It's about orchestrating modular intelligence.\n\nYesterday, I set a 24-hour timer to build a content repurposing pipeline from scratch.\n\nKey takeaways:\n\n• Architecture matters more than lines of code: Modular connectors saved 6 hours of custom integration work.\n• Local-first UX is a superpower: Instant feedback loops keep creators in flow state.\n• Native platform adaptation beats blind cross-posting every single time.\n\nIf you're building in the AI space, what's your biggest bottleneck right now?",
      hashtags: "#SoftwareEngineering #ArtificialIntelligence #ProductManagement #Founders",
      format: "4:5 Portrait Video"
    },
    x: {
      title: "AI SaaS Speedrun",
      caption: "I built an AI SaaS in 24 hours.\n\nNo over-engineering. Just Next.js, FastAPI, and intelligent multi-format pipelines.\n\nHere's the full breakdown of how to repurpose 1 long video into 6 platform assets automatically 🧵👇",
      hashtags: "#buildinpublic #indiehackers",
      format: "Short Clip + Thread"
    },
    youtube: {
      title: "I Built an AI SaaS in 24 Hours (Full Architecture Breakdown)",
      caption: "In this video, I break down the exact architecture behind building an open-source AI content repurposing platform in 24 hours.\n\n⏱️ Chapters:\n00:00 - The 24h Challenge\n02:15 - System Architecture\n05:30 - Media Processing with FFmpeg\n08:45 - AI Platform Generation\n11:20 - Live Demo & Deployment\n\nGitHub Repo link in pinned comment!",
      hashtags: "#ai #programming #fullstack #nextjs #python",
      format: "16:9 Landscape / Shorts"
    },
    tiktok: {
      title: "POV: You build an AI SaaS in 24 hrs",
      caption: "How I built an AI tool in 24 hours using Next.js & Python 🔥 Watch till the end for the tech stack! #coding #tech #softwaredeveloper #fyp #buildinpublic",
      hashtags: "#coding #fyp #developer",
      format: "9:16 Vertical"
    }
  });

  const handleGenerate = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setIsGenerating(false);
    }, 1200);
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Repurpose Studio</h1>
          <p className="text-xs text-gray-400 mt-0.5">Transform single video or media assets into native multi-platform formats.</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 via-purple-600 to-cyan-500 hover:opacity-95 text-white text-xs font-bold shadow-lg shadow-indigo-500/25 transition-all disabled:opacity-50"
          >
            {isGenerating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            <span>{isGenerating ? "Synthesizing AI Outputs..." : "Generate Content"}</span>
          </button>
        </div>
      </div>

      {/* Main Repurpose Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Source Media Player & Format Selector (7 cols) */}
        <div className="lg:col-span-7 space-y-5">
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Source Video</span>
              <span className="text-[11px] text-gray-500 bg-[#161B26] px-2 py-0.5 rounded border border-[#1F2937]">4K • 60fps</span>
            </div>

            <div className="relative aspect-video bg-[#0B0D12] rounded-xl overflow-hidden border border-[#1F2937]/80 flex items-center justify-center group">
              <img
                src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=1000&auto=format&fit=crop&q=80"
                alt="Source preview"
                className="w-full h-full object-cover opacity-80"
              />

              {selectedFormat === '9:16' && (
                <div className="absolute inset-y-0 w-[31.6%] border-2 border-dashed border-indigo-400 bg-indigo-500/10 pointer-events-none flex items-center justify-center">
                  <span className="text-[10px] font-bold text-indigo-200 bg-black/60 px-2 py-0.5 rounded backdrop-blur-sm">
                    9:16 Crop Guide
                  </span>
                </div>
              )}

              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className="absolute w-12 h-12 rounded-full bg-indigo-600/90 text-white flex items-center justify-center shadow-lg hover:scale-110 transition-transform"
              >
                {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
              </button>

              <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/90 to-transparent p-3 flex items-center justify-between text-xs text-gray-300">
                <span className="text-[11px] font-mono">02:45 / 12:42</span>
                <div className="flex items-center gap-3">
                  <Volume2 className="w-4 h-4 cursor-pointer hover:text-white" />
                  <Maximize2 className="w-4 h-4 cursor-pointer hover:text-white" />
                </div>
              </div>
            </div>

            <div className="space-y-2 pt-2">
              <label className="text-xs font-semibold text-gray-300">Target Output Format</label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                {formats.map((fmt) => (
                  <button
                    key={fmt.id}
                    onClick={() => setSelectedFormat(fmt.id)}
                    className={`px-3 py-2.5 rounded-xl text-xs font-semibold border transition-all text-center flex flex-col items-center gap-1 ${
                      selectedFormat === fmt.id
                        ? 'bg-indigo-600/25 border-indigo-500 text-white shadow-md shadow-indigo-500/10'
                        : 'bg-[#161B26] border-[#1F2937] text-gray-400 hover:text-gray-200 hover:border-gray-600'
                    }`}
                  >
                    <span>{fmt.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Destinations & AI Options (5 cols) */}
        <div className="lg:col-span-5 space-y-5">
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3.5">
            <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider block">Destinations</span>
            
            <div className="space-y-2">
              {[
                { key: 'youtube', label: 'YouTube Short', icon: YoutubeIcon, color: 'text-red-400' },
                { key: 'instagram', label: 'Instagram Reel', icon: InstagramIcon, color: 'text-pink-400' },
                { key: 'tiktok', label: 'TikTok', icon: TiktokIcon, color: 'text-cyan-400' },
                { key: 'linkedin', label: 'LinkedIn', icon: LinkedinIcon, color: 'text-blue-400' },
                { key: 'x', label: 'X (Twitter)', icon: XIcon, color: 'text-gray-300' },
                { key: 'facebook', label: 'Facebook', icon: FacebookIcon, color: 'text-blue-500' },
              ].map((dest) => {
                const Icon = dest.icon;
                const isChecked = (destinations as any)[dest.key];
                return (
                  <label
                    key={dest.key}
                    className="flex items-center justify-between p-2.5 rounded-xl bg-[#161B26] border border-[#1F2937] hover:border-gray-700 cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <Icon className={`w-4 h-4 ${dest.color}`} />
                      <span className="text-xs font-medium text-gray-200">{dest.label}</span>
                    </div>
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={(e) => setDestinations({ ...destinations, [dest.key]: e.target.checked })}
                      className="w-4 h-4 rounded text-indigo-600 bg-[#0B0D12] border-gray-700 focus:ring-0 focus:ring-offset-0"
                    />
                  </label>
                );
              })}
            </div>
          </div>

          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider">AI Options</span>
              <span className="text-[10px] text-cyan-400 font-semibold bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">Gemini 1.5 Pro</span>
            </div>

            <div className="space-y-2">
              {[
                { key: 'caption', label: 'Generate caption', icon: Type },
                { key: 'title', label: 'Generate title', icon: FileText },
                { key: 'description', label: 'Generate description', icon: Sliders },
                { key: 'hashtags', label: 'Generate hashtags', icon: Hash },
                { key: 'subtitles', label: 'Generate subtitles (SRT)', icon: Subtitles },
                { key: 'findClips', label: 'Find best viral clips', icon: Scissors },
              ].map((opt) => {
                const Icon = opt.icon;
                const isChecked = (aiOptions as any)[opt.key];
                return (
                  <label
                    key={opt.key}
                    className="flex items-center justify-between p-2 rounded-xl hover:bg-[#161B26] cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-2.5 text-gray-300">
                      <Icon className="w-3.5 h-3.5 text-indigo-400" />
                      <span className="text-xs">{opt.label}</span>
                    </div>
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={(e) => setAiOptions({ ...aiOptions, [opt.key]: e.target.checked })}
                      className="w-4 h-4 rounded text-indigo-600 bg-[#0B0D12] border-gray-700 focus:ring-0 focus:ring-offset-0"
                    />
                  </label>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Generated Platform Outputs Section */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <span>Platform-Specific Outputs</span>
            </h2>
            <p className="text-xs text-gray-400">Tailored copy, constraints, and hashtags per channel.</p>
          </div>

          <div className="flex items-center gap-1 bg-[#161B26] p-1 rounded-xl border border-[#1F2937] overflow-x-auto">
            {Object.keys(generatedOutputs).map((platform) => (
              <button
                key={platform}
                onClick={() => setActiveOutputTab(platform)}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all ${
                  activeOutputTab === platform
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {platform}
              </button>
            ))}
          </div>
        </div>

        {generatedOutputs[activeOutputTab as keyof typeof generatedOutputs] && (
          <div className="bg-[#161B26] border border-[#1F2937] rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white uppercase tracking-wider">
                {activeOutputTab} Formatted Copy
              </span>
              <button
                onClick={() => handleCopy((generatedOutputs as any)[activeOutputTab].caption, activeOutputTab)}
                className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-[#111827] border border-[#1F2937] text-gray-300 hover:text-white text-xs font-medium transition-colors"
              >
                {copiedKey === activeOutputTab ? <CheckCheck className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedKey === activeOutputTab ? "Copied!" : "Copy Copy"}</span>
              </button>
            </div>

            <div>
              <label className="text-[11px] font-medium text-gray-400 block mb-1">Title / Hook</label>
              <input
                type="text"
                value={(generatedOutputs as any)[activeOutputTab].title}
                onChange={(e) => {
                  setGeneratedOutputs({
                    ...generatedOutputs,
                    [activeOutputTab]: { ...generatedOutputs[activeOutputTab as keyof typeof generatedOutputs], title: e.target.value }
                  });
                }}
                className="w-full bg-[#111827] border border-[#1F2937] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="text-[11px] font-medium text-gray-400 block mb-1">Caption / Post Body</label>
              <textarea
                rows={5}
                value={(generatedOutputs as any)[activeOutputTab].caption}
                onChange={(e) => {
                  setGeneratedOutputs({
                    ...generatedOutputs,
                    [activeOutputTab]: { ...generatedOutputs[activeOutputTab as keyof typeof generatedOutputs], caption: e.target.value }
                  });
                }}
                className="w-full bg-[#111827] border border-[#1F2937] rounded-lg p-3 text-xs text-white focus:outline-none focus:border-indigo-500 font-sans"
              />
            </div>

            <div>
              <label className="text-[11px] font-medium text-gray-400 block mb-1">Hashtags</label>
              <input
                type="text"
                value={(generatedOutputs as any)[activeOutputTab].hashtags}
                onChange={(e) => {
                  setGeneratedOutputs({
                    ...generatedOutputs,
                    [activeOutputTab]: { ...generatedOutputs[activeOutputTab as keyof typeof generatedOutputs], hashtags: e.target.value }
                  });
                }}
                className="w-full bg-[#111827] border border-[#1F2937] rounded-lg px-3 py-2 text-xs text-cyan-300 focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>

            <div className="pt-2 flex items-center justify-end gap-3 border-t border-[#1F2937]/80">
              <button className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#111827] border border-[#1F2937] text-gray-300 hover:text-white text-xs font-semibold transition-colors">
                <Clock className="w-3.5 h-3.5 text-amber-400" />
                <span>Schedule to Calendar</span>
              </button>
              <button className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md transition-all">
                <Send className="w-3.5 h-3.5" />
                <span>Publish Now</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
