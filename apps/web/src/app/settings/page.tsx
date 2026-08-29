"use client";

import React, { useState } from 'react';
import { 
  Key, 
  HardDrive, 
  Save, 
  ShieldCheck, 
  Cpu, 
  Check, 
  Sparkles,
  Database,
  Lock
} from 'lucide-react';

export default function SettingsPage() {
  const [saved, setSaved] = useState(false);
  const [apiKeys, setApiKeys] = useState({
    gemini: '••••••••••••••••••••••••••••••••',
    openai: '••••••••••••••••••••••••••••••••',
    anthropic: '',
    storageProvider: 'local',
    storagePath: './storage/reflow_media'
  });

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-12 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Settings & Credentials</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Configure your AI keys, storage provider, and self-hosted environment secrets.
          </p>
        </div>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* AI Provider Section */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <h2 className="text-sm font-bold text-white">Bring Your Own Key (BYOK)</h2>
            </div>
            <span className="text-[11px] text-emerald-400 font-medium bg-emerald-500/10 px-2.5 py-0.5 rounded border border-emerald-500/20">
              Zero SaaS Markup
            </span>
          </div>

          <div className="space-y-3 pt-2">
            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1">Google Gemini API Key</label>
              <div className="relative">
                <input
                  type="password"
                  value={apiKeys.gemini}
                  onChange={(e) => setApiKeys({ ...apiKeys, gemini: e.target.value })}
                  placeholder="AIzaSy..."
                  className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 font-mono"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1">OpenAI API Key</label>
              <div className="relative">
                <input
                  type="password"
                  value={apiKeys.openai}
                  onChange={(e) => setApiKeys({ ...apiKeys, openai: e.target.value })}
                  placeholder="sk-proj-..."
                  className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 font-mono"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Media Storage Provider */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 space-y-4">
          <div className="flex items-center gap-2.5">
            <HardDrive className="w-4 h-4 text-indigo-400" />
            <h2 className="text-sm font-bold text-white">Media Storage Engine</h2>
          </div>

          <div className="space-y-3 pt-2">
            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1">Storage Type</label>
              <select
                value={apiKeys.storageProvider}
                onChange={(e) => setApiKeys({ ...apiKeys, storageProvider: e.target.value })}
                className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="local">Local Filesystem (Zero Config)</option>
                <option value="s3">AWS S3 Compatible</option>
                <option value="r2">Cloudflare R2 (Zero Egress)</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1">Local Storage Path</label>
              <input
                type="text"
                value={apiKeys.storagePath}
                onChange={(e) => setApiKeys({ ...apiKeys, storagePath: e.target.value })}
                className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex items-center justify-end gap-3">
          <button
            type="submit"
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-bold shadow-lg shadow-indigo-500/20 transition-all"
          >
            {saved ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />}
            <span>{saved ? "Settings Saved!" : "Save Changes"}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
