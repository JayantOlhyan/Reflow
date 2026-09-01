"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  Globe, 
  Search, 
  RefreshCw, 
  ShieldCheck, 
  ShieldAlert, 
  Download, 
  CheckCircle2, 
  AlertTriangle, 
  Trash2, 
  ExternalLink, 
  Sparkles, 
  Layers, 
  HardDrive, 
  Cpu, 
  Share2, 
  Puzzle,
  ArrowUpRight,
  Info,
  Sliders,
  Terminal,
  Activity
} from 'lucide-react';
import { EcosystemPluginItem } from '@/types';
import { api } from '@/lib/api';

export default function EcosystemPage() {
  const [plugins, setPlugins] = useState<EcosystemPluginItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedSource, setSelectedSource] = useState<string>('ALL');
  const [installedOnly, setInstalledOnly] = useState<boolean>(false);
  const [updatesOnly, setUpdatesOnly] = useState<boolean>(false);

  // Modal States
  const [installModalPlugin, setInstallModalPlugin] = useState<EcosystemPluginItem | null>(null);
  const [installStep, setInstallStep] = useState<number>(1);
  const [isInstalling, setIsInstalling] = useState<boolean>(false);
  const [installError, setInstallError] = useState<string | null>(null);

  const [updateModalPlugin, setUpdateModalPlugin] = useState<EcosystemPluginItem | null>(null);
  const [isUpdating, setIsUpdating] = useState<boolean>(false);

  const [uninstallModalPlugin, setUninstallModalPlugin] = useState<EcosystemPluginItem | null>(null);
  const [isUninstalling, setIsUninstalling] = useState<boolean>(false);

  useEffect(() => {
    loadCatalog();
  }, [selectedCategory, selectedSource, installedOnly, updatesOnly]);

  const loadCatalog = async () => {
    try {
      setLoading(true);
      const res = await api.getEcosystemPlugins({
        q: searchQuery,
        category: selectedCategory === 'ALL' ? undefined : selectedCategory,
        source: selectedSource === 'ALL' ? undefined : selectedSource,
        installed_only: installedOnly,
        updates_only: updatesOnly
      });
      setPlugins(res.plugins || []);
    } catch (e) {
      console.warn("Failed to load ecosystem catalog:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadCatalog();
  };

  const startInstallFlow = (plugin: EcosystemPluginItem) => {
    setInstallModalPlugin(plugin);
    setInstallStep(1);
    setInstallError(null);
  };

  const executeInstall = async () => {
    if (!installModalPlugin) return;
    try {
      setIsInstalling(true);
      setInstallStep(2); // Review permissions
      await new Promise(r => setTimeout(r, 400));
      setInstallStep(3); // Downloading & Checksum
      await new Promise(r => setTimeout(r, 600));
      setInstallStep(4); // Installing & Health check

      await api.installPlugin(installModalPlugin.id, installModalPlugin.version, installModalPlugin.source_type, true);
      setInstallStep(5); // Ready
      await loadCatalog();
    } catch (err: any) {
      setInstallError(err.message || "Installation failed.");
    } finally {
      setIsInstalling(false);
    }
  };

  const executeUpdate = async () => {
    if (!updateModalPlugin) return;
    try {
      setIsUpdating(true);
      await api.updatePlugin(updateModalPlugin.id, true);
      setUpdateModalPlugin(null);
      await loadCatalog();
    } catch (err: any) {
      alert(`Update failed: ${err.message}`);
    } finally {
      setIsUpdating(false);
    }
  };

  const executeUninstall = async () => {
    if (!uninstallModalPlugin) return;
    try {
      setIsUninstalling(true);
      await api.uninstallPlugin(uninstallModalPlugin.id);
      setUninstallModalPlugin(null);
      await loadCatalog();
    } catch (err: any) {
      alert(`Uninstall failed: ${err.message}`);
    } finally {
      setIsUninstalling(false);
    }
  };

  const categories = [
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
    <div className="p-6 max-w-7xl mx-auto space-y-6 select-none">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Globe className="w-6 h-6 text-indigo-400" />
            <h1 className="text-2xl font-bold text-white tracking-tight">Reflow Integration Hub & Ecosystem</h1>
          </div>
          <p className="text-xs text-slate-400">
            Self-hosted, decentralized plugin ecosystem. Discover and manage community & official platform connectors, AI models, storage drivers, and workflow actions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => { api.refreshEcosystemCatalog(); loadCatalog(); }}
            className="px-3.5 py-2 text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-750 border border-slate-700 rounded-xl flex items-center gap-2 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Catalog</span>
          </button>
        </div>
      </div>

      {/* Filter & Search Toolbar */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-4 bg-slate-900/60 p-3 rounded-2xl border border-slate-800">
        {/* Category Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto w-full md:w-auto">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
                selectedCategory === cat.id
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Search & Source Filter */}
        <div className="flex items-center gap-2 w-full md:w-auto">
          <form onSubmit={handleSearchSubmit} className="relative flex-1 md:w-64">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search catalog..."
              className="w-full pl-9 pr-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </form>

          <select
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value)}
            className="px-3 py-2 bg-slate-800 border border-slate-700 text-xs text-slate-300 rounded-xl focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Sources</option>
            <option value="OFFICIAL">Official</option>
            <option value="COMMUNITY">Community</option>
            <option value="LOCAL">Local</option>
          </select>
        </div>
      </div>

      {/* Catalog Plugins Grid */}
      {loading ? (
        <div className="py-20 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
          <span>Loading ecosystem catalog...</span>
        </div>
      ) : plugins.length === 0 ? (
        <div className="py-16 text-center bg-slate-900/50 border border-dashed border-slate-800 rounded-2xl p-8 space-y-2">
          <Puzzle className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-sm font-semibold text-white">No plugins match your filter</h3>
          <p className="text-xs text-slate-400">Try adjusting your category or search query.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {plugins.map((plugin) => {
            const Icon = getTypeIcon(plugin.plugin_type);
            const isOfficial = plugin.source_type === 'OFFICIAL';
            return (
              <div
                key={plugin.id}
                className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 space-y-4 shadow-lg transition flex flex-col justify-between"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="p-2.5 bg-slate-850 border border-slate-800 rounded-xl text-indigo-400">
                        <Icon className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <Link href={`/ecosystem/${plugin.id}`} className="text-sm font-bold text-white hover:text-indigo-400 transition">
                            {plugin.name}
                          </Link>
                          <span className="text-[10px] font-mono text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded">v{plugin.version}</span>
                        </div>
                        <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">{plugin.description}</p>
                      </div>
                    </div>
                  </div>

                  {/* Badges & Trust */}
                  <div className="flex items-center gap-2 pt-1">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 ${
                      isOfficial 
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    }`}>
                      {isOfficial ? <ShieldCheck className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                      <span>{plugin.source_type}</span>
                    </span>

                    {plugin.is_installed && (
                      <span className="px-2 py-0.5 bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 rounded text-[10px] font-medium flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Installed</span>
                      </span>
                    )}

                    {plugin.update_available && (
                      <span className="px-2 py-0.5 bg-sky-500/10 text-sky-400 border border-sky-500/20 rounded text-[10px] font-medium animate-pulse">
                        Update Available
                      </span>
                    )}
                  </div>

                  {/* Capabilities */}
                  <div className="flex items-center gap-1.5 flex-wrap pt-2 border-t border-slate-800/80">
                    {plugin.capabilities.slice(0, 4).map((cap) => (
                      <span key={cap} className="px-2 py-0.5 bg-slate-800 text-slate-400 rounded text-[10px] font-mono">
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Footer Controls */}
                <div className="flex items-center justify-between pt-4 border-t border-slate-800/80 text-xs">
                  <span className="text-[11px] text-slate-500 font-mono">By {plugin.author}</span>

                  <div className="flex items-center gap-2">
                    {plugin.update_available ? (
                      <button
                        onClick={() => setUpdateModalPlugin(plugin)}
                        className="px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Update</span>
                      </button>
                    ) : plugin.is_installed ? (
                      <button
                        onClick={() => setUninstallModalPlugin(plugin)}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-rose-600/20 text-slate-400 hover:text-rose-400 border border-slate-700 rounded-xl text-xs font-semibold flex items-center gap-1"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span>Uninstall</span>
                      </button>
                    ) : (
                      <button
                        onClick={() => startInstallFlow(plugin)}
                        className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Install</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 7-STEP INSTALL MODAL WITH PERMISSION REVIEWS */}
      {installModalPlugin && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-lg space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-xl">
                  <Download className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-white">Install {installModalPlugin.name}</h2>
                  <p className="text-xs text-slate-400">Version {installModalPlugin.version} • {installModalPlugin.source_type}</p>
                </div>
              </div>
              <span className="text-[11px] font-mono text-slate-500">Step {installStep} of 5</span>
            </div>

            {/* Warning Box */}
            <div className="p-3.5 bg-amber-500/10 border border-amber-500/20 rounded-xl text-xs text-amber-300 space-y-1">
              <div className="flex items-center gap-2 font-semibold">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <span>Security Notice</span>
              </div>
              <p className="text-[11px] text-amber-300/80">
                Installing a plugin grants it the execution permissions declared below. Reflow does not execute unverified arbitrary remote code.
              </p>
            </div>

            {/* Declared Permissions List */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-slate-300">Declared Permissions:</span>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {installModalPlugin.permissions.map((perm) => (
                  <div key={perm} className="px-3 py-1.5 bg-slate-800 border border-slate-750 rounded-lg text-xs font-mono text-indigo-300 flex items-center justify-between">
                    <span>{perm}</span>
                    <span className="text-[10px] text-slate-500">Granted</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Checksum & Digest */}
            <div className="text-xs font-mono text-slate-500 bg-slate-950 p-2.5 rounded-xl border border-slate-850 truncate">
              <span className="text-slate-400">SHA-256 Checksum:</span> {installModalPlugin.checksum}
            </div>

            {installError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl">
                {installError}
              </div>
            )}

            {/* Modal Action Buttons */}
            <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setInstallModalPlugin(null)}
                disabled={isInstalling}
                className="px-4 py-2 bg-slate-800 text-slate-400 rounded-xl text-xs font-semibold hover:bg-slate-750"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={executeInstall}
                disabled={isInstalling}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center gap-2"
              >
                {isInstalling && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>{isInstalling ? `Processing Step ${installStep}...` : "Accept & Install"}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* UPDATE PREVIEW MODAL */}
      {updateModalPlugin && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-md space-y-4 shadow-2xl">
            <h2 className="text-base font-bold text-white">Update {updateModalPlugin.name}</h2>
            <div className="p-3 bg-slate-800 rounded-xl text-xs space-y-2 text-slate-300">
              <div className="flex justify-between">
                <span>Installed Version:</span>
                <span className="font-mono text-slate-400">{updateModalPlugin.installed_version}</span>
              </div>
              <div className="flex justify-between font-bold text-emerald-400">
                <span>Target Version:</span>
                <span className="font-mono">{updateModalPlugin.latest_version}</span>
              </div>
            </div>
            <p className="text-xs text-slate-400">
              Update performs an atomic installation. If health check fails, automated rollback restores version {updateModalPlugin.installed_version}.
            </p>
            <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
              <button onClick={() => setUpdateModalPlugin(null)} className="px-4 py-2 bg-slate-800 text-slate-400 rounded-xl text-xs">
                Cancel
              </button>
              <button onClick={executeUpdate} disabled={isUpdating} className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-xl text-xs font-semibold">
                {isUpdating ? "Updating..." : "Confirm Update"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* UNINSTALL MODAL */}
      {uninstallModalPlugin && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-md space-y-4 shadow-2xl">
            <h2 className="text-base font-bold text-white">Uninstall {uninstallModalPlugin.name}?</h2>
            <p className="text-xs text-slate-400">
              Uninstalling disables plugin execution. Reflow preserves all user publications, content, and historical data created through this plugin.
            </p>
            <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
              <button onClick={() => setUninstallModalPlugin(null)} className="px-4 py-2 bg-slate-800 text-slate-400 rounded-xl text-xs">
                Cancel
              </button>
              <button onClick={executeUninstall} disabled={isUninstalling} className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-semibold">
                {isUninstalling ? "Uninstalling..." : "Confirm Uninstall"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
