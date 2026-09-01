"use client";

import React, { useState, useEffect } from 'react';
import { 
  Puzzle, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  RefreshCw, 
  Power, 
  Shield, 
  Cpu, 
  Layers, 
  HardDrive, 
  Share2, 
  Sparkles,
  Terminal,
  ExternalLink
} from 'lucide-react';
import { PluginItem } from '@/types';
import { api } from '@/lib/api';

export default function PluginsPage() {
  const [plugins, setPlugins] = useState<PluginItem[]>([]);
  const [activeTab, setActiveTab] = useState<string>('ALL');
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    loadPlugins();
  }, [activeTab]);

  const loadPlugins = async () => {
    try {
      setLoading(true);
      const res = await api.getPlugins(activeTab === 'ALL' ? undefined : activeTab);
      setPlugins(res.plugins || []);
    } catch (e) {
      console.warn("Failed to load plugins:", e);
    } finally {
      setLoading(false);
    }
  };

  const togglePlugin = async (plugin: PluginItem) => {
    try {
      setActionLoading(plugin.id);
      if (plugin.enabled) {
        await api.disablePlugin(plugin.id);
      } else {
        await api.enablePlugin(plugin.id);
      }
      await loadPlugins();
    } catch (e: any) {
      alert(`Action failed: ${e.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleHealthCheck = async (id: string) => {
    try {
      setActionLoading(id);
      const res = await api.checkPluginHealth(id);
      alert(`Plugin Health (${id}):\n${JSON.stringify(res, null, 2)}`);
      await loadPlugins();
    } catch (e: any) {
      alert(`Health check failed: ${e.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const tabs = [
    { id: 'ALL', label: 'All Plugins' },
    { id: 'PLATFORM', label: 'Social Platforms' },
    { id: 'AI_PROVIDER', label: 'AI Providers' },
    { id: 'STORAGE', label: 'Storage Drivers' },
    { id: 'MEDIA_PROCESSOR', label: 'Media Processors' },
    { id: 'WORKFLOW_ACTION', label: 'Workflow Actions' }
  ];

  const getTypeIcon = (type: string) => {
    switch (type.toUpperCase()) {
      case 'PLATFORM': return Share2;
      case 'AI_PROVIDER': return Sparkles;
      case 'STORAGE': return HardDrive;
      case 'MEDIA_PROCESSOR': return Cpu;
      case 'WORKFLOW_ACTION': return Layers;
      default: return Puzzle;
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Puzzle className="w-6 h-6 text-indigo-400" />
            <h1 className="text-2xl font-bold text-white tracking-tight">Plugin Ecosystem & Extensibility</h1>
          </div>
          <p className="text-xs text-slate-400">
            Manage built-in and community plugin extensions across platforms, AI providers, storage drivers, and workflow actions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadPlugins}
            className="px-3.5 py-2 text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-750 border border-slate-700 rounded-xl flex items-center gap-2 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Tabs Bar */}
      <div className="flex items-center gap-1 bg-slate-900 p-1.5 rounded-xl border border-slate-800 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition ${
              activeTab === tab.id
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Plugins Grid */}
      {loading ? (
        <div className="py-20 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
          <span>Loading plugin registry...</span>
        </div>
      ) : plugins.length === 0 ? (
        <div className="py-16 text-center bg-slate-900/50 border border-dashed border-slate-800 rounded-2xl p-8 space-y-2">
          <Puzzle className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-sm font-semibold text-white">No plugins found</h3>
          <p className="text-xs text-slate-400">No registered plugins match the selected category filter.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {plugins.map((plugin) => {
            const Icon = getTypeIcon(plugin.type);
            const isWorking = actionLoading === plugin.id;
            return (
              <div
                key={plugin.id}
                className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 space-y-4 shadow-lg transition"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="p-2.5 bg-slate-850 border border-slate-800 rounded-xl text-indigo-400">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-bold text-white">{plugin.name}</h3>
                        <span className="text-[10px] font-mono text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded">v{plugin.version}</span>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">{plugin.description}</p>
                    </div>
                  </div>

                  <button
                    onClick={() => togglePlugin(plugin)}
                    disabled={isWorking}
                    className={`p-2 rounded-xl border transition flex items-center gap-1.5 text-xs font-semibold ${
                      plugin.enabled
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20'
                        : 'bg-slate-800 text-slate-500 border-slate-700 hover:text-white'
                    }`}
                  >
                    <Power className="w-3.5 h-3.5" />
                    <span>{plugin.enabled ? 'Enabled' : 'Disabled'}</span>
                  </button>
                </div>

                {/* Capabilities & Permissions */}
                <div className="space-y-2 pt-2 border-t border-slate-800/80 text-xs">
                  {plugin.capabilities && plugin.capabilities.length > 0 && (
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-slate-500 font-mono text-[10px]">Capabilities:</span>
                      {plugin.capabilities.map((cap) => (
                        <span key={cap} className="px-2 py-0.5 bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 rounded text-[10px]">
                          {cap}
                        </span>
                      ))}
                    </div>
                  )}

                  {plugin.permissions && plugin.permissions.length > 0 && (
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-slate-500 font-mono text-[10px]">Permissions:</span>
                      {plugin.permissions.map((perm) => (
                        <span key={perm} className="px-2 py-0.5 bg-slate-800 text-slate-400 rounded text-[10px]">
                          {perm}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Footer Controls */}
                <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-xs">
                  <div className="flex items-center gap-1.5 text-[11px] font-mono">
                    <span className="text-slate-500">Author: {plugin.author}</span>
                  </div>

                  <button
                    onClick={() => handleHealthCheck(plugin.id)}
                    className="text-xs text-indigo-400 hover:underline font-medium flex items-center gap-1"
                  >
                    <Activity className="w-3.5 h-3.5" />
                    <span>Check Health</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Activity(props: any) {
  return (
    <svg {...props} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  );
}
