"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  Globe, 
  ArrowLeft, 
  ShieldCheck, 
  ShieldAlert, 
  ExternalLink, 
  Download, 
  Trash2, 
  Save, 
  CheckCircle2, 
  History, 
  Share2, 
  Sparkles, 
  HardDrive, 
  Cpu, 
  Layers, 
  Puzzle,
  Lock
} from 'lucide-react';
import { EcosystemPluginItem, PluginAuditLogItem } from '@/types';
import { api } from '@/lib/api';

export default function EcosystemPluginDetailPage() {
  const params = useParams();
  const router = useRouter();
  const pluginId = params.id as string;

  const [plugin, setPlugin] = useState<EcosystemPluginItem | null>(null);
  const [auditLogs, setAuditLogs] = useState<PluginAuditLogItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [configValues, setConfigValues] = useState<Record<string, string>>({
    api_key: '********',
    client_id: '',
    client_secret: '********'
  });
  const [isSavingConfig, setIsSavingConfig] = useState<boolean>(false);
  const [configSuccess, setConfigSuccess] = useState<boolean>(false);

  useEffect(() => {
    if (pluginId) {
      loadDetail();
    }
  }, [pluginId]);

  const loadDetail = async () => {
    try {
      setLoading(true);
      const res = await api.getEcosystemPluginDetail(pluginId);
      setPlugin(res);

      try {
        const logs = await api.getPluginAuditLog(pluginId);
        setAuditLogs(logs || []);
      } catch (e) {
        console.warn("Audit logs fetch error:", e);
      }
    } catch (e) {
      console.warn("Failed to load plugin detail:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSavingConfig(true);
      await api.configurePlugin(pluginId, configValues);
      setConfigSuccess(true);
      setTimeout(() => setConfigSuccess(false), 3000);
      await loadDetail();
    } catch (err: any) {
      alert(`Save config failed: ${err.message}`);
    } finally {
      setIsSavingConfig(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-xs text-slate-500">
        Loading plugin ecosystem metadata...
      </div>
    );
  }

  if (!plugin) {
    return (
      <div className="p-12 text-center space-y-3">
        <h2 className="text-base font-bold text-white">Plugin Not Found</h2>
        <p className="text-xs text-slate-400">The requested plugin '{pluginId}' does not exist in the catalog.</p>
        <Link href="/ecosystem" className="text-xs text-indigo-400 hover:underline">
          Back to Ecosystem Catalog
        </Link>
      </div>
    );
  }

  const isOfficial = plugin.source_type === 'OFFICIAL';

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6 select-none">
      {/* Top Nav Back */}
      <Link href="/ecosystem" className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition">
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Ecosystem Catalog</span>
      </Link>

      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-white tracking-tight">{plugin.name}</h1>
              <span className="text-xs font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded">v{plugin.version}</span>
            </div>
            <p className="text-xs text-slate-400">{plugin.description}</p>
          </div>

          <div className="flex items-center gap-2">
            <span className={`px-3 py-1 rounded-xl text-xs font-bold flex items-center gap-1.5 ${
              isOfficial 
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
            }`}>
              {isOfficial ? <ShieldCheck className="w-4 h-4" /> : <ShieldAlert className="w-4 h-4" />}
              <span>{plugin.source_type}</span>
            </span>
          </div>
        </div>

        {/* Links & Metadata */}
        <div className="flex items-center gap-4 text-xs text-slate-400 pt-2 border-t border-slate-800/80">
          <span>Author: <strong className="text-white">{plugin.author}</strong></span>
          <span>License: <strong className="text-white">{plugin.license || 'MIT'}</strong></span>
          {plugin.repository && (
            <a href={plugin.repository} target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline flex items-center gap-1">
              <span>Repository</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
          {plugin.documentation && (
            <a href={plugin.documentation} target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline flex items-center gap-1">
              <span>Docs</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </div>

      {/* Grid Specs & Usage */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Usage Stats */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2 shadow-lg">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Connections</h3>
          <p className="text-2xl font-bold text-white">{plugin.usage_stats?.active_connections || 0}</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2 shadow-lg">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Publications Created</h3>
          <p className="text-2xl font-bold text-white">{plugin.usage_stats?.publications_created || 0}</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2 shadow-lg">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Automations Using</h3>
          <p className="text-2xl font-bold text-white">{plugin.usage_stats?.automations_using || 0}</p>
        </div>
      </div>

      {/* Permissions & Capabilities */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3 shadow-lg">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider">Capabilities</h3>
          <div className="flex items-center gap-1.5 flex-wrap">
            {plugin.capabilities.map((cap) => (
              <span key={cap} className="px-2.5 py-1 bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 rounded-lg text-xs font-mono">
                {cap}
              </span>
            ))}
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3 shadow-lg">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider">Declared Permissions</h3>
          <div className="space-y-1.5">
            {plugin.permissions.map((perm) => (
              <div key={perm} className="px-3 py-1.5 bg-slate-800 border border-slate-750 rounded-lg text-xs font-mono text-slate-300 flex items-center justify-between">
                <span>{perm}</span>
                <span className="text-[10px] text-emerald-400 font-semibold">Granted</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Configuration Form (Secret Masked) */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-indigo-400" />
            <h2 className="text-sm font-bold text-white">Plugin Configuration & Secret Masking</h2>
          </div>
          {configSuccess && (
            <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Saved securely</span>
            </span>
          )}
        </div>

        <form onSubmit={handleSaveConfig} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">API Key / Token (Secret Masked)</label>
            <input
              type="password"
              value={configValues.api_key}
              onChange={(e) => setConfigValues({ ...configValues, api_key: e.target.value })}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
            />
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={isSavingConfig}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-lg shadow-indigo-600/20"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{isSavingConfig ? "Saving..." : "Save Configuration"}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Audit Log Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
          <History className="w-4 h-4 text-indigo-400" />
          <h2 className="text-sm font-bold text-white">Audit Log History</h2>
        </div>

        {auditLogs.length === 0 ? (
          <p className="text-xs text-slate-500 py-4 text-center">No audit log entries for this plugin.</p>
        ) : (
          <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
            {auditLogs.map((log) => (
              <div key={log.id} className="p-2.5 bg-slate-800/80 border border-slate-750 rounded-xl text-xs flex items-center justify-between font-mono">
                <div className="space-x-2">
                  <span className="px-2 py-0.5 bg-indigo-500/10 text-indigo-300 rounded text-[10px] font-bold">
                    {log.action}
                  </span>
                  <span className="text-slate-400">{JSON.stringify(log.details)}</span>
                </div>
                <span className="text-[10px] text-slate-500">{new Date(log.created_at).toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
