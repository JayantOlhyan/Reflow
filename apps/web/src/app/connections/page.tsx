"use client";

import React, { useState, useEffect } from 'react';
import { ShieldCheck, Share2, AlertCircle, RefreshCw, ExternalLink, CheckCircle2, Lock } from 'lucide-react';
import { PlatformConnectionItem } from '@/types';
import { api } from '@/lib/api';
import { YoutubeIcon, InstagramIcon, TiktokIcon, LinkedinIcon, XIcon, FacebookIcon } from '@/components/ui/SocialIcons';

export default function ConnectionsPage() {
  const [connections, setConnections] = useState<PlatformConnectionItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const loadConnections = async () => {
    try {
      setLoading(true);
      const res = await api.getPlatformConnections();
      setConnections(res.items || []);
    } catch (err: any) {
      setNotification({ type: 'error', message: 'Failed to load platform connections from Reflow API.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConnections();

    // Check URL parameters for OAuth return notifications
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const connectedPlatform = params.get('connected');
      if (connectedPlatform) {
        setNotification({ type: 'success', message: `Successfully connected ${connectedPlatform.toUpperCase()} account with secure encrypted tokens!` });
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
    if (!confirm('Are you sure you want to disconnect this platform account? Publication history will be preserved.')) {
      return;
    }
    try {
      setActionLoading(connectionId);
      await api.disconnectConnection(connectionId);
      setNotification({ type: 'success', message: 'Account disconnected and local tokens securely removed.' });
      await loadConnections();
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to disconnect account.' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleRefreshToken = async (connectionId: string) => {
    try {
      setActionLoading(connectionId);
      await api.refreshConnection(connectionId);
      setNotification({ type: 'success', message: 'Access token refreshed successfully.' });
      await loadConnections();
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to refresh token.' });
    } finally {
      setActionLoading(null);
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
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Platform Connections</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Connect your social channels. OAuth credentials and tokens are AES-256 encrypted at rest on your self-hosted server.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-emerald-400 font-semibold bg-emerald-500/10 px-3 py-1.5 rounded-xl border border-emerald-500/20 flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5" />
            <span>AES-256 Encrypted Tokens at Rest</span>
          </span>
        </div>
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

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {loading ? (
          <div className="col-span-full py-12 text-center text-gray-500">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-400" />
            <p className="text-sm">Loading platform credentials...</p>
          </div>
        ) : (
          connections.map((conn) => {
            const isConnected = conn.status === 'CONNECTED';
            const isReauth = conn.status === 'REAUTH_REQUIRED';

            return (
              <div
                key={conn.id}
                className={`bg-[#111827] border rounded-2xl p-5 space-y-4 transition-all duration-200 ${
                  isConnected
                    ? 'border-emerald-500/30 shadow-[0_4px_20px_rgba(16,185,129,0.05)]'
                    : isReauth
                    ? 'border-amber-500/30'
                    : 'border-[#1F2937]/70'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-[#161B26] border border-[#1F2937] flex items-center justify-center">
                      {getPlatformIcon(conn.platform)}
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                        {conn.name}
                      </h3>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span
                          className={`w-2 h-2 rounded-full ${
                            isConnected
                              ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]'
                              : isReauth
                              ? 'bg-amber-400'
                              : 'bg-gray-600'
                          }`}
                        />
                        <span className="text-[11px] text-gray-400">
                          {isConnected ? 'Connected' : isReauth ? 'Re-auth Required' : 'Not Connected'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  {isConnected ? (
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => handleRefreshToken(conn.id)}
                        disabled={actionLoading === conn.id}
                        title="Refresh Access Token"
                        className="p-1.5 rounded-lg bg-[#161B26] text-gray-400 hover:text-white border border-[#1F2937] transition"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${actionLoading === conn.id ? 'animate-spin' : ''}`} />
                      </button>
                      <button
                        onClick={() => handleDisconnect(conn.id)}
                        disabled={actionLoading === conn.id}
                        className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 transition"
                      >
                        Disconnect
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => handleConnectPlatform(conn.platform)}
                      disabled={actionLoading === conn.platform}
                      className="px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md transition flex items-center gap-1.5"
                    >
                      {actionLoading === conn.platform && <RefreshCw className="w-3 h-3 animate-spin" />}
                      <span>{isReauth ? 'Reconnect' : 'Connect'}</span>
                    </button>
                  )}
                </div>

                {/* Connected Identity */}
                {isConnected && conn.account_name && (
                  <div className="bg-[#161B26] border border-[#1F2937] rounded-xl px-3 py-2.5 flex items-center justify-between text-xs">
                    <span className="text-gray-400">Account:</span>
                    <span className="font-mono font-medium text-white truncate max-w-[180px]">
                      {conn.account_name} {conn.handle ? `(${conn.handle})` : ''}
                    </span>
                  </div>
                )}

                {/* Declared Capabilities */}
                <div className="pt-2 border-t border-[#1F2937]/70 space-y-1.5">
                  <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider block">
                    Supported Capabilities
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {conn.capabilities && conn.capabilities.length > 0 ? (
                      conn.capabilities.map((cap) => (
                        <span key={cap} className="text-[10px] font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                          ✓ {cap.replace('_', ' ')}
                        </span>
                      ))
                    ) : (
                      <span className="text-[10px] font-medium text-gray-400 bg-[#161B26] px-2 py-0.5 rounded border border-[#1F2937]">
                        OAuth Connected
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
