"use client";

import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Share2, 
  AlertCircle, 
  RefreshCw, 
  ExternalLink, 
  CheckCircle2, 
  Lock, 
  Plus, 
  Radio, 
  Folder, 
  Trash2, 
  Play, 
  Zap, 
  X 
} from 'lucide-react';
import { PlatformConnectionItem, InboundSourceItem } from '@/types';
import { api } from '@/lib/api';
import { YoutubeIcon, InstagramIcon, TiktokIcon, LinkedinIcon, XIcon, FacebookIcon } from '@/components/ui/SocialIcons';

export default function ConnectionsPage() {
  const [activeTab, setActiveTab] = useState<'destinations' | 'sources'>('destinations');
  const [connections, setConnections] = useState<PlatformConnectionItem[]>([]);
  const [sources, setSources] = useState<InboundSourceItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Inbound Source Modal
  const [isSourceModalOpen, setIsSourceModalOpen] = useState(false);
  const [sourceName, setSourceName] = useState('');
  const [sourceType, setSourceType] = useState('PODCAST_RSS');
  const [sourceFeedUrl, setSourceFeedUrl] = useState('');
  const [sourceFolderPath, setSourceFolderPath] = useState('');
  const [isSavingSource, setIsSavingSource] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [connRes, srcRes] = await Promise.all([
        api.getPlatformConnections(),
        api.getInboundSources()
      ]);
      setConnections(connRes.items || []);
      setSources(srcRes || []);
    } catch (err: any) {
      setNotification({ type: 'error', message: 'Failed to load connections data.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();

    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const connectedPlatform = params.get('connected');
      if (connectedPlatform) {
        setNotification({ type: 'success', message: `Successfully connected ${connectedPlatform.toUpperCase()} account!` });
        window.history.replaceState({}, '', window.location.pathname);
      } else if (params.get('error')) {
        setNotification({ type: 'error', message: `OAuth authorization error: ${params.get('error')}` });
        window.history.replaceState({}, '', window.location.pathname);
      }
    }
  }, []);

  const handleConnectPlatform = async (platform: string) => {
    try {
      setActionLoading(platform);
      const res = await api.startPlatformOAuth(platform);
      if (res.authorization_url) {
        window.location.href = res.authorization_url;
      }
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || `Failed to initiate ${platform} OAuth consent.` });
      setActionLoading(null);
    }
  };

  const handleDisconnect = async (connectionId: string) => {
    if (!confirm('Are you sure you want to disconnect this platform account?')) return;
    try {
      setActionLoading(connectionId);
      await api.disconnectConnection(connectionId);
      setNotification({ type: 'success', message: 'Account disconnected successfully.' });
      await loadData();
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to disconnect account.' });
    } finally {
      setActionLoading(null);
    }
  };

  const handlePollSource = async (sourceId: string) => {
    try {
      setActionLoading(`poll_${sourceId}`);
      const res = await api.pollInboundSource(sourceId);
      setNotification({ 
        type: 'success', 
        message: `Polled successfully! Ingested ${res.new_items_count || 0} new item(s).` 
      });
      await loadData();
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Polling failed.' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteSource = async (sourceId: string) => {
    if (!confirm('Are you sure you want to delete this inbound source?')) return;
    try {
      await api.deleteInboundSource(sourceId);
      setSources(prev => prev.filter(s => s.id !== sourceId));
      setNotification({ type: 'success', message: 'Inbound source removed.' });
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to delete source.' });
    }
  };

  const handleCreateSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sourceName.trim()) return;

    setIsSavingSource(true);
    try {
      const cfg: Record<string, any> = {};
      if (sourceType === 'PODCAST_RSS') {
        cfg.feed_url = sourceFeedUrl;
      } else if (sourceType === 'LOCAL_FOLDER' || sourceType === 'CLOUD_FOLDER') {
        cfg.folder_path = sourceFolderPath;
      }

      await api.createInboundSource({
        name: sourceName,
        source_type: sourceType,
        config: cfg,
        is_active: true
      });

      setNotification({ type: 'success', message: `Added source '${sourceName}' successfully!` });
      setIsSourceModalOpen(false);
      setSourceName('');
      setSourceFeedUrl('');
      setSourceFolderPath('');
      await loadData();
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to create source.' });
    } finally {
      setIsSavingSource(false);
    }
  };

  const getPlatformIcon = (platform: string) => {
    switch (platform.toLowerCase()) {
      case 'youtube': return <YoutubeIcon className="w-5 h-5 text-red-400" />;
      case 'instagram': return <InstagramIcon className="w-5 h-5 text-pink-400" />;
      case 'tiktok': return <TiktokIcon className="w-5 h-5 text-cyan-400" />;
      case 'linkedin': return <LinkedinIcon className="w-5 h-5 text-blue-400" />;
      case 'x': return <XIcon className="w-4 h-4 text-gray-300" />;
      case 'facebook': return <FacebookIcon className="w-5 h-5 text-blue-500" />;
      default: return <Share2 className="w-5 h-5 text-gray-400" />;
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Connections & Channels</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Manage your outbound publishing destinations and autonomous inbound content sources.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-emerald-400 font-semibold bg-emerald-500/10 px-3 py-1.5 rounded-xl border border-emerald-500/20 flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5" />
            <span>AES-256 Encrypted at Rest</span>
          </span>
          {activeTab === 'sources' && (
            <button
              onClick={() => setIsSourceModalOpen(true)}
              className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md transition-all"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Inbound Source</span>
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-[#1F2937] pb-3">
        <button
          onClick={() => setActiveTab('destinations')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all ${
            activeTab === 'destinations'
              ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
              : 'text-gray-400 hover:text-white hover:bg-[#161B26]'
          }`}
        >
          <Share2 className="w-3.5 h-3.5" />
          <span>Outbound Destinations ({connections.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('sources')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all ${
            activeTab === 'sources'
              ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
              : 'text-gray-400 hover:text-white hover:bg-[#161B26]'
          }`}
        >
          <Zap className="w-3.5 h-3.5" />
          <span>Inbound Sources ({sources.length})</span>
        </button>
      </div>

      {/* Notifications */}
      {notification && (
        <div className={`p-4 rounded-xl flex items-center justify-between border ${
          notification.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-red-500/10 border-red-500/30 text-red-300'
        }`}>
          <div className="flex items-center gap-2 text-sm">
            {notification.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
            <span>{notification.message}</span>
          </div>
          <button onClick={() => setNotification(null)} className="text-xs hover:underline opacity-80">
            Dismiss
          </button>
        </div>
      )}

      {/* Outbound Destinations Tab */}
      {activeTab === 'destinations' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {loading ? (
            <div className="col-span-full py-12 text-center text-gray-500">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-400" />
              <p className="text-sm">Loading destinations...</p>
            </div>
          ) : (
            connections.map(conn => {
              const isConnected = conn.status === 'CONNECTED';
              return (
                <div
                  key={conn.id}
                  className={`bg-[#111827] border rounded-2xl p-5 space-y-4 transition-all duration-200 ${
                    isConnected ? 'border-emerald-500/30 shadow-[0_4px_20px_rgba(16,185,129,0.05)]' : 'border-[#1F2937]/70'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-[#161B26] border border-[#1F2937] flex items-center justify-center">
                        {getPlatformIcon(conn.platform)}
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-white">{conn.name}</h3>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-gray-600'}`} />
                          <span className="text-[11px] text-gray-400">
                            {isConnected ? 'Connected' : 'Not Connected'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {isConnected ? (
                      <button
                        onClick={() => handleDisconnect(conn.id)}
                        disabled={actionLoading === conn.id}
                        className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 transition"
                      >
                        Disconnect
                      </button>
                    ) : (
                      <button
                        onClick={() => handleConnectPlatform(conn.platform)}
                        disabled={actionLoading === conn.platform}
                        className="px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md transition flex items-center gap-1.5"
                      >
                        {actionLoading === conn.platform && <RefreshCw className="w-3 h-3 animate-spin" />}
                        <span>Connect</span>
                      </button>
                    )}
                  </div>

                  {isConnected && conn.account_name && (
                    <div className="bg-[#161B26] border border-[#1F2937] rounded-xl px-3 py-2 flex items-center justify-between text-xs">
                      <span className="text-gray-400">Account:</span>
                      <span className="font-mono font-medium text-white truncate max-w-[180px]">
                        {conn.account_name}
                      </span>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Inbound Sources Tab */}
      {activeTab === 'sources' && (
        <div className="space-y-4">
          {sources.length === 0 ? (
            <div className="text-center py-16 bg-[#111827] border border-[#1F2937] rounded-3xl p-8 space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center mx-auto text-purple-400">
                <Radio className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">No inbound sources added yet</h3>
                <p className="text-xs text-gray-400 max-w-md mx-auto mt-1">
                  Add a Podcast RSS feed or folder watcher to automatically ingest episodes into Reflow without manual uploading.
                </p>
              </div>
              <button
                onClick={() => setIsSourceModalOpen(true)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md transition-all"
              >
                <Plus className="w-4 h-4" />
                <span>Add First Inbound Source</span>
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {sources.map(src => {
                const isPolling = actionLoading === `poll_${src.id}`;
                return (
                  <div
                    key={src.id}
                    className="p-5 rounded-2xl bg-[#111827] border border-[#1F2937] hover:border-gray-700 transition-all space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                          {src.source_type === 'PODCAST_RSS' ? <Radio className="w-5 h-5" /> : <Folder className="w-5 h-5" />}
                        </div>
                        <div>
                          <h3 className="text-sm font-bold text-white">{src.name}</h3>
                          <span className="text-[11px] text-purple-400 font-semibold">{src.source_type}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handlePollSource(src.id)}
                          disabled={isPolling}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#161B26] hover:bg-[#1F2937] border border-[#1F2937] text-gray-300 text-xs font-semibold transition-all disabled:opacity-50"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${isPolling ? 'animate-spin' : ''}`} />
                          <span>{isPolling ? "Polling..." : "Poll Now"}</span>
                        </button>
                        <button
                          onClick={() => handleDeleteSource(src.id)}
                          className="p-1.5 rounded-xl text-gray-400 hover:text-red-400 hover:bg-[#161B26] border border-transparent hover:border-[#1F2937] transition"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    <div className="bg-[#161B26] border border-[#1F2937] rounded-xl p-3 text-xs space-y-1">
                      {src.source_type === 'PODCAST_RSS' && (
                        <div className="truncate text-gray-300">
                          <span className="text-gray-500 mr-1.5">RSS URL:</span>
                          <span className="font-mono">{src.config?.feed_url || "None"}</span>
                        </div>
                      )}
                      {(src.source_type === 'LOCAL_FOLDER' || src.source_type === 'CLOUD_FOLDER') && (
                        <div className="truncate text-gray-300">
                          <span className="text-gray-500 mr-1.5">Watch Path:</span>
                          <span className="font-mono">{src.config?.folder_path || "None"}</span>
                        </div>
                      )}
                      <div className="text-[11px] text-gray-400 flex items-center justify-between pt-1">
                        <span>Last polled: {src.last_polled_at ? new Date(src.last_polled_at).toLocaleString() : 'Never'}</span>
                        <span className="text-emerald-400">● Active Polling (5m)</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Add Inbound Source Modal */}
      {isSourceModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[#111827] border border-[#1F2937] rounded-3xl w-full max-w-lg p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#1F2937] pb-3">
              <h3 className="text-base font-bold text-white">Add Inbound Content Source</h3>
              <button 
                onClick={() => setIsSourceModalOpen(false)}
                className="p-1 rounded-xl text-gray-400 hover:text-white hover:bg-[#161B26]"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateSource} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-300">Source Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. The Tim Ferriss Show RSS"
                  value={sourceName}
                  onChange={e => setSourceName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#161B26] border border-[#1F2937] text-white text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-300">Source Type</label>
                <select
                  value={sourceType}
                  onChange={e => setSourceType(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#161B26] border border-[#1F2937] text-white text-xs focus:outline-none focus:border-indigo-500"
                >
                  <option value="PODCAST_RSS">🎙️ Podcast RSS Feed (Audio/iTunes)</option>
                  <option value="LOCAL_FOLDER">📁 Local Folder Watcher (Drop directory)</option>
                  <option value="CLOUD_FOLDER">☁️ Cloud Storage Watcher (S3 / Drive)</option>
                </select>
              </div>

              {sourceType === 'PODCAST_RSS' && (
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300">Public Podcast RSS Feed URL</label>
                  <input
                    type="url"
                    required
                    placeholder="https://feeds.buzzsprout.com/123456.rss"
                    value={sourceFeedUrl}
                    onChange={e => setSourceFeedUrl(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-[#161B26] border border-[#1F2937] text-white text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>
              )}

              {(sourceType === 'LOCAL_FOLDER' || sourceType === 'CLOUD_FOLDER') && (
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300">Folder Watch Path</label>
                  <input
                    type="text"
                    required
                    placeholder="/path/to/watch_folder"
                    value={sourceFolderPath}
                    onChange={e => setSourceFolderPath(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-[#161B26] border border-[#1F2937] text-white text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setIsSourceModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-[#161B26] hover:bg-[#1F2937] text-gray-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSavingSource}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md transition disabled:opacity-50"
                >
                  {isSavingSource ? "Saving..." : "Add Source"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
