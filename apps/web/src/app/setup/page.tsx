"use client";

import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  RefreshCw, 
  Server, 
  HardDrive, 
  Cpu, 
  Layers, 
  Sparkles, 
  Link2,
  ArrowRight,
  ShieldCheck
} from 'lucide-react';
import { api } from '@/lib/api';
import Link from 'next/link';

interface CheckItem {
  id: string;
  label: string;
  description: string;
  status: 'PASS' | 'WARNING' | 'FAIL' | 'CHECKING';
  details?: string;
  icon: any;
  actionUrl?: string;
  actionText?: string;
}

export default function SetupPage() {
  const [loading, setLoading] = useState(true);
  const [overallStatus, setOverallStatus] = useState<'READY' | 'ACTION REQUIRED' | 'CHECKING'>('CHECKING');
  const [checklist, setChecklist] = useState<CheckItem[]>([
    {
      id: 'database',
      label: 'PostgreSQL Database',
      description: 'Relational storage for contents, jobs, and publications',
      status: 'CHECKING',
      icon: Server
    },
    {
      id: 'storage',
      label: 'Media Storage Engine',
      description: 'Persistent volume access for raw assets, clips, and exports',
      status: 'CHECKING',
      icon: HardDrive
    },
    {
      id: 'ffmpeg',
      label: 'FFmpeg Video Transcoder',
      description: 'Frame-accurate sub-clipping and thumbnail rendering engine',
      status: 'CHECKING',
      icon: Cpu
    },
    {
      id: 'redis',
      label: 'Redis Job Queue',
      description: 'Asynchronous task distribution and rate-limiting queue',
      status: 'CHECKING',
      icon: Layers
    },
    {
      id: 'ai',
      label: 'AI Provider Keys (BYOK)',
      description: 'Google Gemini or OpenAI API keys for copy synthesis and clipping',
      status: 'CHECKING',
      icon: Sparkles,
      actionUrl: '/settings',
      actionText: 'Configure Keys'
    },
    {
      id: 'connections',
      label: 'Platform OAuth Connections',
      description: 'Active credentials for YouTube, Instagram, X, LinkedIn, etc.',
      status: 'CHECKING',
      icon: Link2,
      actionUrl: '/connections',
      actionText: 'Manage Connections'
    }
  ]);

  const runChecklist = async () => {
    setLoading(true);
    try {
      const readyRes = await api.getReadinessStatus();
      const deps = readyRes.dependencies || {};

      const connections = await api.getConnections().catch(() => []);
      const activeConnections = connections.filter((c: any) => c.status === 'CONNECTED');

      setChecklist(prev => prev.map(item => {
        if (item.id === 'database') {
          const dbStatus = deps.database?.status;
          return {
            ...item,
            status: dbStatus === 'healthy' ? 'PASS' : 'FAIL',
            details: deps.database?.details || 'Database connection status'
          };
        }
        if (item.id === 'storage') {
          const stStatus = deps.storage?.status;
          return {
            ...item,
            status: stStatus === 'healthy' ? 'PASS' : 'FAIL',
            details: deps.storage?.details || 'Storage read/write test'
          };
        }
        if (item.id === 'ffmpeg') {
          const ffStatus = deps.ffmpeg?.status;
          return {
            ...item,
            status: ffStatus === 'healthy' ? 'PASS' : 'FAIL',
            details: deps.ffmpeg?.details || 'FFmpeg binary status'
          };
        }
        if (item.id === 'redis') {
          const rdStatus = deps.redis?.status;
          return {
            ...item,
            status: rdStatus === 'healthy' ? 'PASS' : rdStatus === 'not_configured' ? 'WARNING' : 'WARNING',
            details: deps.redis?.details || 'Redis connection status'
          };
        }
        if (item.id === 'ai') {
          const aiStatus = deps.ai?.status;
          return {
            ...item,
            status: aiStatus === 'healthy' ? 'PASS' : 'WARNING',
            details: deps.ai?.details || 'AI provider key configuration'
          };
        }
        if (item.id === 'connections') {
          return {
            ...item,
            status: activeConnections.length > 0 ? 'PASS' : 'WARNING',
            details: activeConnections.length > 0 
              ? `${activeConnections.length} platform connection(s) active` 
              : 'No platform accounts connected yet'
          };
        }
        return item;
      }));

      const isReady = (
        deps.database?.status === 'healthy' &&
        deps.storage?.status === 'healthy' &&
        deps.ffmpeg?.status === 'healthy'
      );
      setOverallStatus(isReady ? 'READY' : 'ACTION REQUIRED');
    } catch (err: any) {
      setOverallStatus('ACTION REQUIRED');
      setChecklist(prev => prev.map(item => ({
        ...item,
        status: 'FAIL',
        details: 'Reflow backend is unavailable or restarting.'
      })));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runChecklist();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PASS':
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>PASS</span>
          </span>
        );
      case 'WARNING':
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>WARNING</span>
          </span>
        );
      case 'FAIL':
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3.5 h-3.5" />
            <span>FAIL</span>
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-gray-700/20 text-gray-400 border border-gray-600">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            <span>CHECKING</span>
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-12 max-w-4xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <ShieldCheck className="w-6 h-6 text-indigo-400" />
            <span>First-Run Setup Checklist</span>
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Verify self-hosted infrastructure, AI configuration, and platform connections.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={runChecklist}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-[#111827] border border-[#1F2937] text-xs font-semibold text-gray-300 hover:text-white hover:bg-[#161B26] transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Re-verify Setup</span>
          </button>

          <span className={`px-3 py-1 rounded-xl text-xs font-extrabold border tracking-wide uppercase ${
            overallStatus === 'READY' 
              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' 
              : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
          }`}>
            {overallStatus}
          </span>
        </div>
      </div>

      {/* Overview Status Card */}
      <div className={`border rounded-2xl p-5 space-y-2 ${
        overallStatus === 'READY'
          ? 'bg-emerald-950/20 border-emerald-500/30'
          : 'bg-amber-950/20 border-amber-500/30'
      }`}>
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white">System Status Summary</h2>
          <span className="text-xs text-gray-400 font-mono">Reflow v1.0.0</span>
        </div>
        <p className="text-xs text-gray-300">
          {overallStatus === 'READY'
            ? 'All essential Reflow infrastructure services (Database, Storage, and FFmpeg) are operational. Your environment is ready to process and publish content.'
            : 'Action is required to complete system setup. Ensure PostgreSQL, storage permissions, and FFmpeg are available.'}
        </p>
      </div>

      {/* Checklist Grid */}
      <div className="space-y-3">
        {checklist.map(item => {
          const Icon = item.icon;
          return (
            <div 
              key={item.id}
              className="bg-[#111827] border border-[#1F2937] rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 transition-all hover:border-gray-700"
            >
              <div className="flex items-start gap-3.5">
                <div className="p-2.5 rounded-xl bg-[#161B26] border border-[#1F2937] text-indigo-400 mt-0.5">
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-white">{item.label}</h3>
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">{item.description}</p>
                  {item.details && (
                    <p className="text-[11px] font-mono text-gray-500 mt-1">{item.details}</p>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between sm:justify-end gap-3 pt-2 sm:pt-0 border-t sm:border-0 border-[#1F2937]">
                {item.actionUrl && (
                  <Link
                    href={item.actionUrl}
                    className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
                  >
                    <span>{item.actionText}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                )}
                {getStatusBadge(item.status)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
