"use client";

import React, { useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { 
  Activity, 
  Layers, 
  FileText, 
  RotateCcw, 
  Terminal, 
  Server, 
  Cpu, 
  Sparkles
} from 'lucide-react';
import { PublishingJob, SystemLog } from '@/types';

function SystemContent() {
  const searchParams = useSearchParams();
  const initialTab = searchParams.get('tab') || 'health';
  const [activeTab, setActiveTab] = useState<string>(initialTab);

  const [jobs, setJobs] = useState<PublishingJob[]>([
    { id: 'job-1', content_title: 'Instagram Reel (Building in Public Day 20)', platform: 'instagram', status: 'published', time: '2m ago', retry_count: 0 },
    { id: 'job-2', content_title: 'YouTube Short (AI Automation System)', platform: 'youtube', status: 'processing', time: '5m ago', retry_count: 0 },
    { id: 'job-3', content_title: 'LinkedIn Post (10 Lessons from building)', platform: 'linkedin', status: 'scheduled', time: '1h ago', retry_count: 0 },
    { id: 'job-4', content_title: 'X Post (Quick update on the build)', platform: 'x', status: 'published', time: '2h ago', retry_count: 0 },
    { id: 'job-5', content_title: 'TikTok Video (Behind the scenes)', platform: 'tiktok', status: 'failed', time: '3h ago', retry_count: 2, error: 'Token expired or missing permissions' }
  ]);

  const [logs] = useState<SystemLog[]>([
    { id: 'log-1', level: 'INFO', timestamp: '15:30:12', service: 'MediaWorker', message: 'FFmpeg transcoding completed for asset cnt-1 (1080x1920 9:16 vertical output generated)' },
    { id: 'log-2', level: 'INFO', timestamp: '15:31:05', service: 'AIEngine', message: 'AI platform copy generation succeeded for Instagram, LinkedIn, X, and YouTube' },
    { id: 'log-3', level: 'INFO', timestamp: '15:32:00', service: 'Publisher', message: 'Instagram Reel published successfully (ID: ig_8941249)' },
    { id: 'log-4', level: 'WARN', timestamp: '15:33:14', service: 'Publisher', message: 'TikTok publishing API returned rate-limit delay; queued for automatic backoff retry #1' },
    { id: 'log-5', level: 'ERROR', timestamp: '15:34:50', service: 'Publisher', message: 'TikTok publishing failed after retry #2: OAuth scope missing or expired session' }
  ]);

  const handleRetryJob = (jobId: string) => {
    setJobs(jobs.map(j => {
      if (j.id === jobId) {
        return { ...j, status: 'processing', retry_count: j.retry_count + 1 };
      }
      return j;
    }));

    setTimeout(() => {
      setJobs(prev => prev.map(j => {
        if (j.id === jobId) {
          return { ...j, status: 'published', time: 'Just now' };
        }
        return j;
      }));
    }, 1500);
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">System & Operations</h1>
          <p className="text-xs text-gray-400 mt-0.5">Real-time health telemetry, asynchronous job queues, and structured logs.</p>
        </div>

        <div className="flex items-center gap-1 bg-[#111827] p-1 rounded-xl border border-[#1F2937]">
          {[
            { id: 'health', label: 'Health', icon: Activity },
            { id: 'jobs', label: 'Jobs', icon: Layers },
            { id: 'logs', label: 'Logs', icon: FileText },
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === tab.id
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {activeTab === 'health' && (
        <div className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">Database Layer</span>
                <Server className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                <span className="text-sm font-bold text-white">SQLite / PostgreSQL</span>
              </div>
              <p className="text-xs text-gray-400">Persistent local store connected and responding in 2ms.</p>
            </div>

            <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">Media Engine</span>
                <Cpu className="w-4 h-4 text-purple-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                <span className="text-sm font-bold text-white">FFmpeg 8.1+</span>
              </div>
              <p className="text-xs text-gray-400">Native binary detected; GPU acceleration enabled for transcoding.</p>
            </div>

            <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">AI Service</span>
                <Sparkles className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                <span className="text-sm font-bold text-white">Gemini & OpenAI</span>
              </div>
              <p className="text-xs text-gray-400">Multi-provider router active with automated fallback.</p>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'jobs' && (
        <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">Publishing Job Queue</h3>
            <span className="text-xs text-gray-400">Active background workers: 4</span>
          </div>

          <div className="divide-y divide-[#1F2937]">
            {jobs.map((job) => (
              <div key={job.id} className="py-3 flex items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-white">{job.content_title}</span>
                    <span className="text-[10px] font-mono uppercase text-gray-400 bg-[#161B26] px-2 py-0.5 rounded border border-[#1F2937]">
                      {job.platform}
                    </span>
                  </div>
                  {job.error && (
                    <p className="text-[11px] text-rose-400 mt-1">{job.error}</p>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-md ${
                    job.status === 'published' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                    job.status === 'processing' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 animate-pulse' :
                    job.status === 'scheduled' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                    'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                  }`}>
                    {job.status}
                  </span>

                  {job.status === 'failed' && (
                    <button
                      onClick={() => handleRetryJob(job.id)}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-600/20 hover:bg-indigo-600 text-indigo-300 hover:text-white border border-indigo-500/30 text-xs font-medium transition-all"
                    >
                      <RotateCcw className="w-3 h-3" />
                      <span>Retry</span>
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'logs' && (
        <div className="bg-[#0B0D12] border border-[#1F2937] rounded-2xl p-5 space-y-3 font-mono text-xs shadow-inner">
          <div className="flex items-center justify-between pb-2 border-b border-[#1F2937] text-gray-400">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-indigo-400" />
              <span className="font-bold">Structured System Logs</span>
            </div>
            <span className="text-[11px]">Streaming live</span>
          </div>

          <div className="space-y-2">
            {logs.map((log) => (
              <div key={log.id} className="flex items-start gap-3 text-[11px] leading-relaxed">
                <span className="text-gray-500">{log.timestamp}</span>
                <span className={`font-bold px-1.5 py-0.2 rounded text-[10px] ${
                  log.level === 'INFO' ? 'text-cyan-400 bg-cyan-950/40' :
                  log.level === 'WARN' ? 'text-amber-400 bg-amber-950/40' :
                  'text-rose-400 bg-rose-950/40'
                }`}>
                  {log.level}
                </span>
                <span className="text-indigo-300 font-semibold">[{log.service}]</span>
                <span className="text-gray-300">{log.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function SystemPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs text-gray-500">Loading System Telemetry...</div>}>
      <SystemContent />
    </Suspense>
  );
}
