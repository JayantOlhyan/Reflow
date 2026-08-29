"use client";

import React, { useState } from 'react';
import { ShieldCheck, Share2 } from 'lucide-react';
import { SocialAccount } from '@/types';
import { YoutubeIcon, InstagramIcon, TiktokIcon, LinkedinIcon, XIcon, FacebookIcon } from '@/components/ui/SocialIcons';

export default function ConnectionsPage() {
  const [connections, setConnections] = useState<SocialAccount[]>([
    { id: 'youtube', name: 'YouTube', handle: '@JayantOlhyan', connected: true, capabilities: ['Video', 'Shorts', 'Thumbnails', 'Scheduling'] },
    { id: 'instagram', name: 'Instagram', handle: '@jayantolhyan', connected: true, capabilities: ['Reels', 'Carousels', 'Images', 'Scheduling'] },
    { id: 'tiktok', name: 'TikTok', handle: '@jayant.olhyan', connected: true, capabilities: ['Videos', 'Captions', 'Scheduling'] },
    { id: 'linkedin', name: 'LinkedIn', handle: 'Jayant Olhyan', connected: true, capabilities: ['Posts', 'Carousels (PDF)', 'Videos', 'Scheduling'] },
    { id: 'x', name: 'X (Twitter)', handle: '@JayantOlhyan', connected: true, capabilities: ['Tweets', 'Threads', 'Media', 'Scheduling'] },
    { id: 'facebook', name: 'Facebook', handle: '', connected: false, capabilities: ['Posts', 'Videos', 'Images', 'Scheduling'] },
    { id: 'pinterest', name: 'Pinterest', handle: '', connected: false, capabilities: ['Pins', 'Idea Pins', 'Scheduling'] },
    { id: 'threads', name: 'Threads', handle: '', connected: false, capabilities: ['Text', 'Media', 'Scheduling'] }
  ]);

  const toggleConnection = (id: string) => {
    setConnections(connections.map((c) => {
      if (c.id === id) {
        return {
          ...c,
          connected: !c.connected,
          handle: !c.connected ? `@jayant_${id}` : ''
        };
      }
      return c;
    }));
  };

  const getPlatformIcon = (id: string) => {
    switch (id) {
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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Platform Connections</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Connect your personal or creator accounts. Tokens are stored locally on your self-hosted server.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-emerald-400 font-semibold bg-emerald-500/10 px-3 py-1 rounded-xl border border-emerald-500/20 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>100% User-Owned Credentials</span>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {connections.map((conn) => (
          <div
            key={conn.id}
            className={`bg-[#111827] border rounded-2xl p-5 space-y-4 transition-all duration-200 ${
              conn.connected ? 'border-[#1F2937] hover:border-indigo-500/40' : 'border-[#1F2937]/60 opacity-80'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-[#161B26] border border-[#1F2937] flex items-center justify-center">
                  {getPlatformIcon(conn.id)}
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">{conn.name}</h3>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className={`w-2 h-2 rounded-full ${conn.connected ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]' : 'bg-gray-600'}`} />
                    <span className="text-[11px] text-gray-400">
                      {conn.connected ? 'Connected' : 'Not connected'}
                    </span>
                  </div>
                </div>
              </div>

              <button
                onClick={() => toggleConnection(conn.id)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  conn.connected
                    ? 'bg-[#161B26] hover:bg-[#1F2937] text-gray-300 border border-[#1F2937]'
                    : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-md'
                }`}
              >
                {conn.connected ? 'Manage' : 'Connect'}
              </button>
            </div>

            {conn.connected && (
              <div className="bg-[#161B26] border border-[#1F2937] rounded-xl px-3 py-2 flex items-center justify-between text-xs">
                <span className="text-gray-400">Account:</span>
                <span className="font-mono font-medium text-white">{conn.handle}</span>
              </div>
            )}

            <div className="pt-2 border-t border-[#1F2937]/70 space-y-1.5">
              <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider block">
                Declared Capabilities
              </span>
              <div className="flex flex-wrap gap-1">
                {conn.capabilities.map((cap) => (
                  <span
                    key={cap}
                    className="text-[10px] font-medium text-gray-400 bg-[#161B26] px-2 py-0.5 rounded border border-[#1F2937]"
                  >
                    {cap}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
