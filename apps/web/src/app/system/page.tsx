"use client";

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
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
  BarChart2,
  AlertTriangle,
  ShieldAlert,
  Sliders,
  CheckCircle2,
  XCircle,
  Play
} from 'lucide-react';
import { DeadLetterJobItem, SystemIncidentItem, SystemLog } from '@/types';
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

  const [metrics, setMetrics] = useState<{
    status: string;
    cpu: { usage_percent: number; count: number } | null;
    memory: { total_mb: number; used_mb: number; free_mb: number; usage_percent: number } | null;
    disk: { total_gb: number; used_gb: number; free_gb: number; usage_percent: number; warning: boolean } | null;
  } | null>(null);

  const [dlqJobs, setDlqJobs] = useState<DeadLetterJobItem[]>([]);
  const [incidents, setIncidents] = useState<SystemIncidentItem[]>([]);
  const [telemetryMetrics, setTelemetryMetrics] = useState<any>(null);
  const [maintenanceMode, setMaintenanceMode] = useState<boolean>(false);
  const [retryingJobId, setRetryingJobId] = useState<string | null>(null);
  const [logs, setLogs] = useState<SystemLog[]>([]);
  const [performanceData, setPerformanceData] = useState<any>(null);
  const [storageBreakdown, setStorageBreakdown] = useState<any>(null);
  const [cleaningStorage, setCleaningStorage] = useState<boolean>(false);

  const loadSystemData = async () => {
    try {
      setLoading(true);
      const health = await api.getSystemHealth();
      setHealthData(health);
      const metricsData = await api.getSystemMetrics().catch(() => null);
      setMetrics(metricsData);
      const perfData = await api.getSystemPerformance().catch(() => null);
      setPerformanceData(perfData);
      const storageData = await api.getStorageBreakdown().catch(() => null);
      setStorageBreakdown(storageData);
      const failedJobs = await api.getFailedJobs().catch(() => []);
      setDlqJobs(failedJobs);
      const incList = await api.getIncidents({ status: 'OPEN' }).catch(() => []);
      setIncidents(incList);
      const telem = await api.getSystemTelemetryMetrics().catch(() => null);
      setTelemetryMetrics(telem);
      const fetchedLogs = await api.getSystemLogs();
      setLogs(fetchedLogs);
    } catch (err) {
      console.warn("Failed to load system telemetry:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCleanStorage = async () => {
    setCleaningStorage(true);
    try {
      const res = await api.cleanTemporaryStorage();
      alert(`Cleaned up ${res.message || 'temporary files'}. Freed ${res.freed_mb} MB.`);
      await loadSystemData();
    } catch (err: any) {
      alert(`Storage cleanup failed: ${err.message || err}`);
    } finally {
      setCleaningStorage(false);
    }
  };

  useEffect(() => {
    loadSystemData();
  }, []);

  const handleRetryJob = async (jobId: string) => {
    setRetryingJobId(jobId);
    try {
      await api.retryFailedJob(jobId);
      await loadSystemData();
    } catch (err) {
      alert(`Retry failed: ${err}`);
    } finally {
      setRetryingJobId(null);
    }
  };

  const handleToggleMaintenance = async () => {
    const target = !maintenanceMode;
    try {
      const res = await api.setSystemMaintenanceMode(target);
      setMaintenanceMode(res.maintenance_mode);
    } catch (err) {
      alert(`Failed to toggle maintenance mode: ${err}`);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'HEALTHY':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
      case 'degraded':
      case 'DEGRADED':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      case 'not_configured':
        return 'text-gray-400 bg-gray-700/20 border-gray-600';
      case 'unavailable':
      case 'UNHEALTHY':
      default:
        return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Maintenance Mode Operational Banner */}
      {maintenanceMode && (
        <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-2xl flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ShieldAlert className="w-5 h-5 text-amber-400" />
            <div>
              <h3 className="text-sm font-bold text-amber-300">Reflow is in Maintenance Mode</h3>
              <p className="text-xs text-amber-400/80">Outbound automatic publishing and scheduled automations are temporarily paused by operator request.</p>
            </div>
          </div>
          <button
            onClick={handleToggleMaintenance}
            className="px-3 py-1.5 bg-amber-500 text-black font-semibold rounded-xl text-xs hover:bg-amber-400 transition-colors"
          >
            Disable Maintenance Mode
          </button>
        </div>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">System & Operations Hub</h1>
          <p className="text-xs text-gray-400 mt-0.5">Real-time health telemetry, Dead-Letter Queue (DLQ), trace timelines, and incident monitoring.</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleToggleMaintenance}
            className={`px-3 py-2 rounded-xl text-xs font-semibold border flex items-center gap-1.5 transition-colors ${
              maintenanceMode
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                : 'bg-[#111827] text-gray-400 border-[#1F2937] hover:text-white'
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>{maintenanceMode ? 'Maintenance ON' : 'Maintenance Mode'}</span>
          </button>

          <button
            onClick={loadSystemData}
            className="p-2 text-gray-400 hover:text-white rounded-xl bg-[#111827] border border-[#1F2937] hover:bg-[#161B26] transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <div className="flex items-center gap-1 bg-[#111827] p-1 rounded-xl border border-[#1F2937]">
            {[
              { id: 'health', label: 'Health', icon: Activity },
              { id: 'incidents', label: `Incidents (${incidents.length})`, icon: AlertTriangle },
              { id: 'jobs', label: `DLQ Jobs (${dlqJobs.length})`, icon: Layers },
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

      {/* Active Incidents Banner */}
      {incidents.length > 0 && (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-2xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-400" />
            <div>
              <h3 className="text-sm font-bold text-rose-300">{incidents.length} Active System Incidents</h3>
              <p className="text-xs text-rose-400/80">{incidents[0].title} ({incidents[0].component})</p>
            </div>
          </div>
          <Link
            href="/system/incidents"
            className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-500 text-white font-semibold rounded-xl text-xs transition-colors"
          >
            View Incident Hub →
          </Link>
        </div>
      )}

      {activeTab === 'health' && (
        <div className="space-y-5">
          {/* Resource Telemetry */}
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-indigo-400" />
                <h2 className="text-sm font-bold text-white">System Resource Telemetry</h2>
              </div>
              <span className={`text-xs font-bold px-2 py-0.5 rounded border ${
                metrics?.status === 'AVAILABLE'
                  ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                  : 'text-gray-400 bg-gray-700/20 border-gray-600'
              }`}>
                {metrics?.status === 'AVAILABLE' ? 'REALTIME METRICS' : 'UNAVAILABLE'}
              </span>
            </div>

            {metrics?.status === 'AVAILABLE' ? (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-xs">
                <div className="bg-[#161B26] p-3 rounded-xl border border-[#1F2937] space-y-1">
                  <span className="text-gray-400 text-[11px]">CPU Usage</span>
                  <p className="text-lg font-bold text-white">{metrics.cpu?.usage_percent}%</p>
                  <p className="text-[10px] text-gray-500">{metrics.cpu?.count} Cores Available</p>
                </div>

                <div className="bg-[#161B26] p-3 rounded-xl border border-[#1F2937] space-y-1">
                  <span className="text-gray-400 text-[11px]">RAM Memory</span>
                  <p className="text-lg font-bold text-white">{metrics.memory?.usage_percent}%</p>
                  <p className="text-[10px] text-gray-500">{metrics.memory?.used_mb}MB / {metrics.memory?.total_mb}MB</p>
                </div>

                <div className="bg-[#161B26] p-3 rounded-xl border border-[#1F2937] space-y-1">
                  <span className="text-gray-400 text-[11px]">Disk Storage</span>
                  <p className={`text-lg font-bold ${metrics.disk?.warning ? 'text-amber-400' : 'text-white'}`}>
                    {metrics.disk?.usage_percent}%
                  </p>
                  <p className="text-[10px] text-gray-500">{metrics.disk?.used_gb}GB / {metrics.disk?.total_gb}GB</p>
                </div>
              </div>
            ) : (
              <div className="p-4 bg-[#161B26] rounded-xl border border-[#1F2937] text-xs text-gray-400 font-mono">
                System resource metrics (psutil) are currently UNAVAILABLE on this host environment.
              </div>
            )}
          </div>

          {/* Histogram Telemetry Stats */}
          {telemetryMetrics && (
            <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-4">
              <div className="flex items-center gap-2">
                <BarChart2 className="w-4 h-4 text-cyan-400" />
                <h2 className="text-sm font-bold text-white">Execution Latency Histograms</h2>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-xs">
                <div className="bg-[#161B26] p-3 rounded-xl border border-[#1F2937] space-y-1">
                  <span className="text-gray-400 text-[11px]">Media Processing Latency</span>
                  <p className="text-sm font-bold text-white">p50: {telemetryMetrics.jobs?.duration_histogram?.p50_ms || 0}ms</p>
                  <p className="text-[10px] text-gray-500">p90: {telemetryMetrics.jobs?.duration_histogram?.p90_ms || 0}ms | p99: {telemetryMetrics.jobs?.duration_histogram?.p99_ms || 0}ms</p>
                </div>
                <div className="bg-[#161B26] p-3 rounded-xl border border-[#1F2937] space-y-1">
                  <span className="text-gray-400 text-[11px]">Publication Dispatch Latency</span>
                  <p className="text-sm font-bold text-white">p50: {telemetryMetrics.publications?.duration_histogram?.p50_ms || 0}ms</p>
                  <p className="text-[10px] text-gray-500">p90: {telemetryMetrics.publications?.duration_histogram?.p90_ms || 0}ms | p99: {telemetryMetrics.publications?.duration_histogram?.p99_ms || 0}ms</p>
                </div>
                <div className="bg-[#161B26] p-3 rounded-xl border border-[#1F2937] space-y-1">
                  <span className="text-gray-400 text-[11px]">API Request Duration</span>
                  <p className="text-sm font-bold text-white">p50: {telemetryMetrics.api?.request_duration_histogram?.p50_ms || 0}ms</p>
                  <p className="text-[10px] text-gray-500">p90: {telemetryMetrics.api?.request_duration_histogram?.p90_ms || 0}ms | p99: {telemetryMetrics.api?.request_duration_histogram?.p99_ms || 0}ms</p>
                </div>
              </div>
            </div>
          )}

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
              <p className="text-xs text-gray-400">{healthData.components.database?.details || "PostgreSQL / SQLite"}</p>
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
              <p className="text-xs text-gray-400">{healthData.components.redis?.details || "In-Memory / Optional"}</p>
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
              <p className="text-xs text-gray-400">{healthData.components.ai?.details || "Gemini / OpenAI Active"}</p>
            </div>

            {/* Scheduler Engine Component */}
            <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">Scheduler Daemon</span>
                <Clock className="w-4 h-4 text-amber-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-bold capitalize border ${getStatusColor(healthData.components.scheduler?.status || 'healthy')}`}>
                  {healthData.components.scheduler?.status || 'healthy'}
                </span>
              </div>
              <p className="text-xs text-gray-400">{healthData.components.scheduler?.details || "UTC Scheduler Heartbeat Active"}</p>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'incidents' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">Active & Recent Incidents</h3>
            <Link
              href="/system/incidents"
              className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
            >
              Open Full Incident Hub →
            </Link>
          </div>
          {incidents.length === 0 ? (
            <div className="py-12 text-center text-xs text-gray-500 bg-[#111827] border border-[#1F2937] rounded-2xl">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
              <p className="font-semibold text-gray-300">No active incidents</p>
              <p className="text-[11px] text-gray-500">System components and jobs are operating cleanly.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {incidents.map((inc) => (
                <div key={inc.id} className="bg-[#111827] border border-[#1F2937] rounded-2xl p-4 flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 bg-rose-500/20 text-rose-300 text-[10px] font-bold rounded">
                        {inc.severity}
                      </span>
                      <h4 className="text-xs font-bold text-white">{inc.title}</h4>
                    </div>
                    <p className="text-xs text-gray-400">{inc.description}</p>
                  </div>
                  <Link
                    href={`/system/incidents`}
                    className="px-3 py-1.5 bg-[#161B26] hover:bg-[#1F2937] text-white text-xs font-semibold rounded-xl border border-[#1F2937] transition-colors"
                  >
                    Inspect
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'jobs' && (
        <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white">Dead-Letter Queue (DLQ) Inspector</h3>
              <p className="text-xs text-gray-400">Permanently failed or exhausted background jobs requiring manual operator intervention.</p>
            </div>
            <span className="text-xs font-mono text-gray-400">DLQ Items: {dlqJobs.length}</span>
          </div>

          {dlqJobs.length === 0 ? (
            <div className="py-12 text-center text-xs text-gray-500">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
              <p className="font-semibold text-gray-300">Dead-Letter Queue is Empty</p>
              <p className="text-[11px] text-gray-500">No permanently failed jobs registered.</p>
            </div>
          ) : (
            <div className="divide-y divide-[#1F2937]">
              {dlqJobs.map((job) => (
                <div key={job.id} className="py-3 flex items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-white">Job #{job.job_id} ({job.job_type})</span>
                      <span className="px-2 py-0.5 bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[10px] font-bold rounded">
                        {job.error_code || 'FAILED'}
                      </span>
                    </div>
                    {job.last_error && (
                      <p className="text-[11px] text-rose-400 font-mono">{job.last_error}</p>
                    )}
                    <p className="text-[10px] text-gray-500">Failed at: {job.failed_at} | Attempts: {job.attempts}</p>
                  </div>

                  <button
                    onClick={() => handleRetryJob(job.job_id)}
                    disabled={retryingJobId === job.job_id}
                    className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl flex items-center gap-1.5 transition-colors disabled:opacity-50"
                  >
                    <RotateCcw className={`w-3.5 h-3.5 ${retryingJobId === job.job_id ? 'animate-spin' : ''}`} />
                    <span>Retry Job</span>
                  </button>
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
            <span className="text-[11px]">Live Server Logs</span>
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
