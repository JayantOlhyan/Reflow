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
  ShieldCheck,
  Check,
  ChevronRight,
  Upload,
  Settings
} from 'lucide-react';
import { api } from '@/lib/api';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

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
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [overallStatus, setOverallStatus] = useState<'READY' | 'ACTION REQUIRED' | 'CHECKING'>('CHECKING');
  
  // API Key Inputs
  const [geminiKey, setGeminiKey] = useState<string>('');
  const [openaiKey, setOpenaiKey] = useState<string>('');
  const [keySaveMessage, setKeySaveMessage] = useState<string | null>(null);

  const [checklist, setChecklist] = useState<CheckItem[]>([
    { id: 'database', label: 'PostgreSQL Database', description: 'Relational storage for contents & publications', status: 'CHECKING', icon: Server },
    { id: 'storage', label: 'Media Storage Engine', description: 'Persistent volume access for raw assets & clips', status: 'CHECKING', icon: HardDrive },
    { id: 'ffmpeg', label: 'FFmpeg Transcoder', description: 'Frame-accurate sub-clipping & thumbnail rendering', status: 'CHECKING', icon: Cpu },
    { id: 'redis', label: 'Redis Job Queue', description: 'Asynchronous task queue & worker synchronization', status: 'CHECKING', icon: Layers },
    { id: 'ai', label: 'AI Provider Keys (BYOK)', description: 'Gemini or OpenAI API key configured', status: 'CHECKING', icon: Sparkles },
    { id: 'connections', label: 'Platform Connections', description: 'Active OAuth connections for publishing', status: 'CHECKING', icon: Link2 }
  ]);

  useEffect(() => {
    runChecklist();
  }, []);

  const runChecklist = async () => {
    setLoading(true);
    try {
      const readyRes = await api.getReadinessStatus();
      const deps = readyRes.dependencies || {};
      const connections = await api.getConnections().catch(() => []);
      const activeConnections = connections.filter((c: any) => c.status === 'CONNECTED');

      setChecklist(prev => prev.map(item => {
        if (item.id === 'database') {
          return { ...item, status: deps.database?.status === 'healthy' ? 'PASS' : 'FAIL', details: deps.database?.details };
        }
        if (item.id === 'storage') {
          return { ...item, status: deps.storage?.status === 'healthy' ? 'PASS' : 'FAIL', details: deps.storage?.details };
        }
        if (item.id === 'ffmpeg') {
          return { ...item, status: deps.ffmpeg?.status === 'healthy' ? 'PASS' : 'FAIL', details: deps.ffmpeg?.details };
        }
        if (item.id === 'redis') {
          return { ...item, status: deps.redis?.status === 'healthy' ? 'PASS' : 'FAIL', details: deps.redis?.details };
        }
        if (item.id === 'ai') {
          const aiHealthy = deps.ai_providers?.status === 'healthy';
          return {
            ...item,
            status: aiHealthy ? 'PASS' : 'WARNING',
            details: aiHealthy ? 'AI Provider key detected & verified' : 'No AI provider key configured'
          };
        }
        if (item.id === 'connections') {
          const hasConn = activeConnections.length > 0;
          return {
            ...item,
            status: hasConn ? 'PASS' : 'WARNING',
            details: hasConn ? `${activeConnections.length} platform(s) connected` : 'Zero active platform connections'
          };
        }
        return item;
      }));

      const isReady = readyRes.ready;
      setOverallStatus(isReady ? 'READY' : 'ACTION REQUIRED');
    } catch (e) {
      console.warn("Failed to check readiness:", e);
      setOverallStatus('ACTION REQUIRED');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveKeys = async () => {
    try {
      await api.updateSystemSettings({
        gemini_api_key: geminiKey || undefined,
        openai_api_key: openaiKey || undefined
      });
      setKeySaveMessage("API keys updated successfully!");
      runChecklist();
    } catch (e: any) {
      setKeySaveMessage(`Failed: ${e.message}`);
    }
  };

  const steps = [
    { num: 1, name: 'System Check' },
    { num: 2, name: 'Storage' },
    { num: 3, name: 'AI Configuration' },
    { num: 4, name: 'Platform Connections' },
    { num: 5, name: 'Brand Rules' },
    { num: 6, name: 'Launch Workspace' }
  ];

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-8">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-indigo-400" />
            <h1 className="text-2xl font-bold text-white tracking-tight">First-Run Onboarding & Setup</h1>
          </div>
          <p className="text-xs text-slate-400">
            Step-by-step verification of backend services, media storage, AI keys, platform credentials, and workspace launch.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className={`px-3 py-1 rounded-full text-xs font-bold border ${
            overallStatus === 'READY'
              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
              : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
          }`}>
            Status: {overallStatus}
          </span>
          <button
            onClick={runChecklist}
            className="p-2 text-slate-400 hover:text-white bg-slate-800 border border-slate-700 rounded-xl text-xs flex items-center gap-1.5"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Re-check</span>
          </button>
        </div>
      </div>

      {/* Step Indicator */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
        {steps.map(s => (
          <button
            key={s.num}
            onClick={() => setCurrentStep(s.num)}
            className={`p-3 rounded-xl border text-center transition ${
              currentStep === s.num
                ? 'bg-indigo-600 border-indigo-500 text-white shadow-lg shadow-indigo-600/20'
                : currentStep > s.num
                ? 'bg-slate-850/80 border-slate-750 text-indigo-300'
                : 'bg-slate-900 border-slate-800 text-slate-500'
            }`}
          >
            <div className="text-[10px] font-mono opacity-75">Step {s.num}</div>
            <div className="text-xs font-semibold truncate">{s.name}</div>
          </button>
        ))}
      </div>

      {/* STEP CONTENT PANELS */}

      {/* STEP 1: SYSTEM READINESS CHECK */}
      {currentStep === 1 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
          <h2 className="text-base font-semibold text-white">Step 1: Core Service Health Checks</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {checklist.map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.id} className="p-4 bg-slate-850 rounded-xl border border-slate-800 flex items-start space-x-3">
                  <div className="p-2.5 rounded-lg bg-slate-800 text-indigo-400 mt-0.5">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold text-white">{item.label}</h4>
                      <span className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                        item.status === 'PASS' ? 'bg-emerald-500/20 text-emerald-300' :
                        item.status === 'WARNING' ? 'bg-amber-500/20 text-amber-300' : 'bg-rose-500/20 text-rose-300'
                      }`}>
                        {item.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">{item.description}</p>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="flex justify-end pt-4">
            <button
              onClick={() => setCurrentStep(2)}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5"
            >
              <span>Next: Storage Setup</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: MEDIA STORAGE */}
      {currentStep === 2 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <h2 className="text-base font-semibold text-white">Step 2: Media Storage Directory</h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            Reflow stores raw media assets, audio extractions, FFmpeg sub-clips, and carousel PDF exports on local persistent storage under <code className="text-indigo-300 font-mono">./storage/</code>.
          </p>

          <div className="p-4 bg-slate-850 rounded-xl border border-slate-800 space-y-2 text-xs">
            <div className="flex justify-between"><span className="text-slate-400">Storage Provider:</span><span className="text-white font-mono">LOCAL_DISK</span></div>
            <div className="flex justify-between"><span className="text-slate-400">Base Path:</span><span className="text-white font-mono">./storage/content/</span></div>
            <div className="flex justify-between"><span className="text-slate-400">Max Upload Limit:</span><span className="text-white font-mono">500 MB</span></div>
          </div>

          <div className="flex justify-between pt-4">
            <button onClick={() => setCurrentStep(1)} className="px-4 py-2 text-xs text-slate-400 hover:text-white">← Back</button>
            <button onClick={() => setCurrentStep(3)} className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5">
              <span>Next: AI Keys</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: AI PROVIDER KEYS */}
      {currentStep === 3 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <h2 className="text-base font-semibold text-white">Step 3: Configure AI API Keys (Bring Your Own Key)</h2>
          <p className="text-xs text-slate-400">
            Configure Google Gemini or OpenAI API keys for transcript summary, clipping analysis, and copy generation.
          </p>

          {keySaveMessage && (
            <div className="p-3 bg-indigo-500/20 border border-indigo-500/40 rounded-xl text-indigo-300 text-xs">
              {keySaveMessage}
            </div>
          )}

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Google Gemini API Key</label>
              <input
                type="password"
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                placeholder="AIzaSy..."
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">OpenAI API Key (Optional)</label>
              <input
                type="password"
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <button
              onClick={handleSaveKeys}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-750 text-white rounded-xl text-xs font-semibold border border-slate-700 transition"
            >
              Save API Keys
            </button>
          </div>

          <div className="flex justify-between pt-4">
            <button onClick={() => setCurrentStep(2)} className="px-4 py-2 text-xs text-slate-400 hover:text-white">← Back</button>
            <button onClick={() => setCurrentStep(4)} className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5">
              <span>Next: Connections</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: PLATFORM CONNECTIONS */}
      {currentStep === 4 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <h2 className="text-base font-semibold text-white">Step 4: Platform OAuth Connections</h2>
          <p className="text-xs text-slate-400">
            Connect target social channels to enable automated multi-platform publishing.
          </p>

          <div className="flex items-center justify-between p-4 bg-slate-850 rounded-xl border border-slate-800">
            <div>
              <div className="text-sm font-semibold text-white">Platform Credentials & OAuth</div>
              <div className="text-xs text-slate-400 mt-0.5">Manage YouTube, LinkedIn, X, Instagram, TikTok credentials.</div>
            </div>
            <Link
              href="/connections"
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold"
            >
              Open Connections Page →
            </Link>
          </div>

          <div className="flex justify-between pt-4">
            <button onClick={() => setCurrentStep(3)} className="px-4 py-2 text-xs text-slate-400 hover:text-white">← Back</button>
            <button onClick={() => setCurrentStep(5)} className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5">
              <span>Next: Brand Rules</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 5: BRAND RULES */}
      {currentStep === 5 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <h2 className="text-base font-semibold text-white">Step 5: Brand Profile & Quality Rules</h2>
          <p className="text-xs text-slate-400">
            Define tone, forbidden terms, and mandatory hashtags to ensure automated content adheres to governance policies.
          </p>

          <div className="p-4 bg-slate-850 rounded-xl border border-slate-800 text-xs space-y-2">
            <div className="flex justify-between"><span className="text-slate-400">Default Governance Policy:</span><span className="text-emerald-400 font-semibold">ACTIVE (Strict)</span></div>
            <div className="flex justify-between"><span className="text-slate-400">Claim Verification:</span><span className="text-white">Enabled</span></div>
          </div>

          <div className="flex justify-between pt-4">
            <button onClick={() => setCurrentStep(4)} className="px-4 py-2 text-xs text-slate-400 hover:text-white">← Back</button>
            <button onClick={() => setCurrentStep(6)} className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5">
              <span>Next: Launch Workspace</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 6: LAUNCH WORKSPACE */}
      {currentStep === 6 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center space-y-6">
          <div className="w-16 h-16 bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 rounded-2xl flex items-center justify-center mx-auto">
            <Check className="w-8 h-8" />
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-white tracking-tight">Onboarding Complete!</h2>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Your Reflow deployment is configured and ready. You can now upload your first source video or text note.
            </p>
          </div>

          <div className="flex justify-center gap-4 pt-2">
            <Link
              href="/content"
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-indigo-600/25 transition"
            >
              Open Content Library
            </Link>
            <Link
              href="/"
              className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold border border-slate-700 transition"
            >
              Go to Overview Dashboard
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
