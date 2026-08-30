"use client";

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { 
  Activity, 
  Layers, 
  FileText, 
  RotateCcw, 
  Terminal, 
  Server, 
  Cpu, 
  Sparkles,
  HardDrive,
  RefreshCw,
  Clock,
  BarChart2
} from 'lucide-react';
import { PublishingJob, SystemLog } from '@/types';
import { api } from '@/lib/api';

function SystemContent() {
  const searchParams = useSearchParams();
  const initialTab = searchParams.get('tab') || 'health';
  const [activeTab, setActiveTab] = useState<string>(initialTab);
  const [loading, setLoading] = useState(true);

  const [healthData, setHealthData] = useState<{
    status: string;
    timestamp: string;
    components: Record<string, { status: string; details?: string }>;
  }>({
    status: "checking",
    timestamp: "",
    components: {
      database: { status: "checking" },
      storage: { status: "checking" },
      ffmpeg: { status: "checking" },
      redis: { status: "checking" },
      ai: { status: "checking" }
    }
  });

  const [jobs, setJobs] = useState<PublishingJob[]>([]);
  const [logs, setLogs] = useState<SystemLog[]>([]);

  const loadSystemData = async () => {
    try {
      setLoading(true);
      const health = await api.getSystemHealth();
      setHealthData(health);
      const fetchedJobs = await api.getSystemJobs();
      setJobs(fetchedJobs);
      const fetchedLogs = await api.getSystemLogs();
      setLogs(fetchedLogs);
    } catch (err) {
      console.warn("Failed to load system telemetry:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSystemData();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
      case 'degraded':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      case 'not_configured':
        return 'text-gray-400 bg-gray-700/20 border-gray-600';
      case 'unavailable':
      default:
        return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">System & Operations</h1>
          <p className="text-xs text-gray-400 mt-0.5">Real-time health telemetry, asynchronous job queues, and structured logs.</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadSystemData}
            className="p-2 text-gray-400 hover:text-white rounded-xl bg-[#111827] border border-[#1F2937] hover:bg-[#161B26] transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>

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
      </div>

      {activeTab === 'health' && (
        <div className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* Database Component */}
            <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">Database</span>
                <Server className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-bold capitalize border ${getStatusColor(healthData.components.database?.status)}`}>
                  {healthData.components.database?.status}
                </span>
              </div>
              <p className="text-xs text-gray-400">{healthData.components.database?.details || "SQLite / PostgreSQL"}</p>
            </div>

            {/* Storage Component */}
            <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">Storage Engine</span>
                <HardDrive className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-bold capitalize border ${getStatusColor(healthData.components.storage?.status)}`}>
                  {healthData.components.storage?.status}
                </span>
              </div>
              <p className="text-xs text-gray-400">{healthData.components.storage?.details || "Local Filesystem"}</p>
            </div>

            {/* FFmpeg Component */}
            <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">FFmpeg Binary</span>
                <Cpu className="w-4 h-4 text-purple-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-bold capitalize border ${getStatusColor(healthData.components.ffmpeg?.status)}`}>
                  {healthData.components.ffmpeg?.status}
                </span>
              </div>
              <p className="text-xs text-gray-400 truncate">{healthData.components.ffmpeg?.details || "FFmpeg Transcoder"}</p>
            </div>

            {/* Redis Component */}
            <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">Redis Queue</span>
                <Layers className="w-4 h-4 text-red-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-bold capitalize border ${getStatusColor(healthData.components.redis?.status)}`}>
                  {healthData.components.redis?.status}
                </span>
              </div>
              <p className="text-xs text-gray-400">{healthData.components.redis?.details || "In-Memory / Optional in Phase 0"}</p>
            </div>

            {/* AI Providers Component */}
            <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">AI Providers</span>
                <Sparkles className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-bold capitalize border ${getStatusColor(healthData.components.ai?.status)}`}>
                  {healthData.components.ai?.status}
                </span>
              </div>
              <p className="text-xs text-gray-400">{healthData.components.ai?.details || "Offline Mock Active"}</p>
            </div>

            {/* Scheduler Engine Component (Phase 9) */}
            <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">Scheduler Engine</span>
                <Clock className="w-4 h-4 text-amber-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-bold capitalize border ${getStatusColor(healthData.components.scheduler?.status || 'idle')}`}>
                  {healthData.components.scheduler?.status || 'Active'}
                </span>
              </div>
              <p className="text-xs text-gray-400">{healthData.components.scheduler?.details || "UTC Server-Side Daemon"}</p>
            </div>

            {/* Analytics Engine Component (Phase 10) */}
            <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">Analytics Engine</span>
                <BarChart2 className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-bold capitalize border ${getStatusColor(healthData.components.analytics?.status || 'healthy')}`}>
                  {healthData.components.analytics?.status || 'Active'}
                </span>
              </div>
              <p className="text-xs text-gray-400">{healthData.components.analytics?.details || "Async Metric Ingestion & Snapshots"}</p>
            </div>

            {/* Content Intelligence Engine Component (Phase 11) */}
            <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">Content Intelligence</span>
                <Sparkles className="w-4 h-4 text-primary" />
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-bold capitalize border ${getStatusColor(healthData.components.intelligence?.status || 'healthy')}`}>
                  {healthData.components.intelligence?.status || 'Active'}
                </span>
              </div>
              <p className="text-xs text-gray-400">{healthData.components.intelligence?.details || "Pattern Detection & Anti-Hallucination Recs"}</p>
            </div>

            {/* Experimentation Engine Component (Phase 12) */}
            <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">Experiment Engine</span>
                <Activity className="w-4 h-4 text-violet-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-bold capitalize border ${getStatusColor(healthData.components.experiment_engine?.status || 'healthy')}`}>
                  {healthData.components.experiment_engine?.status || 'Active'}
                </span>
              </div>
              <p className="text-xs text-gray-400">{healthData.components.experiment_engine?.details || "Statistical A/B Verification & Z-Test Math"}</p>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'jobs' && (
        <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">Publishing Job Queue</h3>
            <span className="text-xs text-gray-400">Total jobs: {jobs.length}</span>
          </div>

          {jobs.length === 0 ? (
            <div className="py-12 text-center text-xs text-gray-500">
              <Clock className="w-8 h-8 text-gray-600 mx-auto mb-2" />
              <p className="font-semibold text-gray-400">No active background jobs</p>
              <p className="text-[11px]">Jobs will appear here when content processing and scheduling runs.</p>
            </div>
          ) : (
            <div className="divide-y divide-[#1F2937]">
              {jobs.map((job) => (
                <div key={job.id} className="py-3 flex items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-white">{job.content_title || job.type}</span>
                    </div>
                    {job.error && (
                      <p className="text-[11px] text-rose-400 mt-1">{job.error}</p>
                    )}
                  </div>

                  <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-md ${
                    job.status === 'SUCCEEDED' || job.status === 'published' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                    job.status === 'RUNNING' || job.status === 'processing' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 animate-pulse' :
                    job.status === 'QUEUED' || job.status === 'scheduled' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                    'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                  }`}>
                    {job.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'logs' && (
        <div className="bg-[#0B0D12] border border-[#1F2937] rounded-2xl p-5 space-y-3 font-mono text-xs shadow-inner">
          <div className="flex items-center justify-between pb-2 border-b border-[#1F2937] text-gray-400">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-indigo-400" />
              <span className="font-bold">Structured System Logs</span>
            </div>
            <span className="text-[11px]">Live Database Logs</span>
          </div>

          {logs.length === 0 ? (
            <div className="py-12 text-center text-xs text-gray-600 font-mono">
              [No log records registered in database yet]
            </div>
          ) : (
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
          )}
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
