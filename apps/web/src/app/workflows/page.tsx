"use client";

import React, { useState } from 'react';
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
  Sliders
} from 'lucide-react';
import { YoutubeIcon, InstagramIcon, TiktokIcon, LinkedinIcon, XIcon } from '@/components/ui/SocialIcons';

export default function WorkflowsPage() {
  const [activeWorkflow, setActiveWorkflow] = useState({
    id: 'wf-1',
    name: 'YouTube to Everywhere',
    active: true,
    description: 'Automatically repurpose long YouTube videos into vertical Reels, Shorts, TikToks, and text summaries.',
    trigger: 'YouTube New Video'
  });

  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationStep, setSimulationStep] = useState(0);

  const handleRunSimulation = () => {
    setIsSimulating(true);
    setSimulationStep(1);
    setTimeout(() => setSimulationStep(2), 800);
    setTimeout(() => setSimulationStep(3), 1600);
    setTimeout(() => {
      setSimulationStep(4);
      setTimeout(() => setIsSimulating(false), 1200);
    }, 2400);
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">{activeWorkflow.name}</h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Active
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">{activeWorkflow.description}</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunSimulation}
            disabled={isSimulating}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#161B26] hover:bg-[#1F2937] border border-[#1F2937] text-gray-300 hover:text-white text-xs font-semibold transition-all disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5 text-emerald-400" />
            <span>{isSimulating ? "Simulating Run..." : "Test Run"}</span>
          </button>
          <button
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-md transition-all"
          >
            <Save className="w-3.5 h-3.5" />
            <span>Save & Publish</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-2 bg-[#111827] border border-[#1F2937] rounded-2xl p-4 space-y-3">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block px-1">
            Components
          </span>

          <div className="space-y-1.5">
            {[
              { label: 'Trigger', icon: Zap, color: 'text-amber-400' },
              { label: 'Action / AI', icon: Sparkles, color: 'text-indigo-400' },
              { label: 'Filter', icon: Filter, color: 'text-cyan-400' },
              { label: 'Delay', icon: Clock, color: 'text-purple-400' },
              { label: 'Split', icon: Split, color: 'text-pink-400' },
              { label: 'Output', icon: Share2, color: 'text-emerald-400' },
            ].map((comp) => {
              const Icon = comp.icon;
              return (
                <div
                  key={comp.label}
                  className="flex items-center gap-2.5 p-2.5 rounded-xl bg-[#161B26] border border-[#1F2937] text-xs font-medium text-gray-300 hover:text-white hover:border-gray-600 cursor-grab active:cursor-grabbing transition-colors"
                >
                  <Icon className={`w-3.5 h-3.5 ${comp.color}`} />
                  <span>{comp.label}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="lg:col-span-7 bg-[#0B0D12] border border-[#1F2937] rounded-2xl p-6 relative overflow-hidden min-h-[550px] flex flex-col justify-center">
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#1F293715_1px,transparent_1px),linear-gradient(to_bottom,#1F293715_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none" />

          <div className="relative z-10 space-y-8 max-w-xl mx-auto w-full">
            <div className={`p-4 rounded-2xl border transition-all duration-300 flex items-center justify-between ${
              simulationStep >= 1 ? 'bg-indigo-600/25 border-indigo-500 shadow-lg shadow-indigo-500/20' : 'bg-[#111827] border-[#1F2937]'
            }`}>
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-red-500/20 border border-red-500/30 flex items-center justify-center">
                  <YoutubeIcon className="w-4 h-4 text-red-400" />
                </div>
                <div>
                  <span className="text-[10px] font-bold text-red-400 uppercase">Trigger</span>
                  <h4 className="text-xs font-bold text-white">YouTube New Video</h4>
                </div>
              </div>
              <span className="text-[11px] text-gray-400 bg-[#161B26] px-2 py-0.5 rounded">Channel Upload</span>
            </div>

            <div className="w-0.5 h-6 bg-gradient-to-b from-indigo-500 to-purple-500 mx-auto" />

            <div className={`p-4 rounded-2xl border transition-all duration-300 flex items-center justify-between ${
              simulationStep >= 2 ? 'bg-purple-600/25 border-purple-500 shadow-lg shadow-purple-500/20' : 'bg-[#111827] border-[#1F2937]'
            }`}>
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-purple-500/20 border border-purple-500/30 flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-purple-400" />
                </div>
                <div>
                  <span className="text-[10px] font-bold text-purple-400 uppercase">AI Processing</span>
                  <h4 className="text-xs font-bold text-white">AI Repurpose Engine</h4>
                </div>
              </div>
              <span className="text-[11px] text-gray-400 bg-[#161B26] px-2 py-0.5 rounded">Multi-Platform</span>
            </div>

            <div className="w-0.5 h-6 bg-gradient-to-b from-purple-500 to-cyan-500 mx-auto" />

            <div className={`p-4 rounded-2xl border transition-all duration-300 flex items-center justify-between ${
              simulationStep >= 3 ? 'bg-cyan-600/25 border-cyan-500 shadow-lg shadow-cyan-500/20' : 'bg-[#111827] border-[#1F2937]'
            }`}>
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center">
                  <Split className="w-4 h-4 text-cyan-400" />
                </div>
                <div>
                  <span className="text-[10px] font-bold text-cyan-400 uppercase">Transform</span>
                  <h4 className="text-xs font-bold text-white">Split Content Formats</h4>
                </div>
              </div>
              <span className="text-[11px] text-gray-400 bg-[#161B26] px-2 py-0.5 rounded">Video, Text, Carousel</span>
            </div>

            <div className="w-0.5 h-6 bg-gradient-to-b from-cyan-500 to-emerald-500 mx-auto" />

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
              {[
                { name: 'Instagram', label: 'Reel (9:16)', icon: InstagramIcon, color: 'text-pink-400' },
                { name: 'TikTok', label: 'Video (9:16)', icon: TiktokIcon, color: 'text-cyan-400' },
                { name: 'Shorts', label: 'Short (9:16)', icon: YoutubeIcon, color: 'text-red-400' },
                { name: 'LinkedIn', label: 'Post (Text)', icon: LinkedinIcon, color: 'text-blue-400' },
                { name: 'X', label: 'Thread', icon: XIcon, color: 'text-gray-300' },
              ].map((dest) => {
                const Icon = dest.icon;
                return (
                  <div
                    key={dest.name}
                    className={`p-2.5 rounded-xl border text-center transition-all ${
                      simulationStep >= 4
                        ? 'bg-emerald-500/20 border-emerald-500 shadow-md'
                        : 'bg-[#111827] border-[#1F2937]'
                    }`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${dest.color} mx-auto mb-1`} />
                    <span className="text-[10px] font-bold text-white block">{dest.name}</span>
                    <span className="text-[9px] text-gray-400">{dest.label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="lg:col-span-3 bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-4">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block">
            Workflow Properties
          </span>

          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-gray-400 block mb-1">Workflow Name</label>
              <input
                type="text"
                value={activeWorkflow.name}
                onChange={(e) => setActiveWorkflow({ ...activeWorkflow, name: e.target.value })}
                className="w-full bg-[#161B26] border border-[#1F2937] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-gray-400 block mb-1">Description</label>
              <textarea
                rows={3}
                value={activeWorkflow.description}
                onChange={(e) => setActiveWorkflow({ ...activeWorkflow, description: e.target.value })}
                className="w-full bg-[#161B26] border border-[#1F2937] rounded-lg p-3 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-gray-400 block mb-1">Trigger Event</label>
              <select
                value={activeWorkflow.trigger}
                onChange={(e) => setActiveWorkflow({ ...activeWorkflow, trigger: e.target.value })}
                className="w-full bg-[#161B26] border border-[#1F2937] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="YouTube New Video">YouTube New Video</option>
                <option value="Manual Upload">Manual File Upload</option>
                <option value="Scheduled Cron">Scheduled Cron</option>
                <option value="Webhook / RSS">Webhook / RSS Feed</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
