'use client';

import React, { useState, useEffect } from 'react';
import {
  Key,
  Webhook,
  Code,
  Plus,
  Trash2,
  Copy,
  Check,
  Shield,
  Send,
  ExternalLink,
  BookOpen,
  Terminal,
  AlertCircle
} from 'lucide-react';
import { api } from '@/lib/api';

const ALL_SCOPES = [
  'CONTENT_READ', 'CONTENT_WRITE',
  'CLIP_READ', 'CLIP_WRITE',
  'CAROUSEL_READ', 'CAROUSEL_WRITE',
  'PUBLISH',
  'ANALYTICS_READ',
  'EXPERIMENT_READ', 'EXPERIMENT_WRITE',
  'AUTOMATION_READ', 'AUTOMATION_WRITE',
  'GOVERNANCE_READ', 'GOVERNANCE_WRITE',
  'WEBHOOK_READ', 'WEBHOOK_WRITE'
];

export default function DeveloperPortalPage() {
  const [activeTab, setActiveTab] = useState<'keys' | 'webhooks' | 'sdks'>('keys');
  const [apiKeys, setApiKeys] = useState<any[]>([]);
  const [webhooks, setWebhooks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Key creation modal state
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [keyName, setKeyName] = useState('');
  const [selectedScopes, setSelectedScopes] = useState<string[]>(['CONTENT_READ', 'CONTENT_WRITE', 'PUBLISH']);
  const [rawKeyRevealed, setRawKeyRevealed] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);

  // Webhook creation state
  const [showWebhookModal, setShowWebhookModal] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState('');
  const [selectedWebhookEvents, setSelectedWebhookEvents] = useState<string[]>(['content.created', 'publication.succeeded']);
  const [webhookCreatedSecret, setWebhookCreatedSecret] = useState<string | null>(null);

  useEffect(() => {
    loadDeveloperData();
  }, []);

  async function loadDeveloperData() {
    setLoading(true);
    try {
      const keysRes = await api.getApiKeys();
      setApiKeys(keysRes || []);
      const webhooksRes = await api.getWebhooks();
      setWebhooks(webhooksRes || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateKey(e: React.FormEvent) {
    e.preventDefault();
    if (!keyName.trim()) return;
    try {
      const res = await api.createApiKey(keyName, selectedScopes);
      setRawKeyRevealed(res.raw_key);
      setShowKeyModal(false);
      setKeyName('');
      loadDeveloperData();
    } catch (err: any) {
      alert(err.message || 'Failed to create API key');
    }
  }

  async function handleRevokeKey(id: string) {
    if (!confirm('Are you sure you want to revoke this API key? Applications using it will immediately lose access.')) return;
    try {
      await api.revokeApiKey(id);
      loadDeveloperData();
    } catch (err: any) {
      alert(err.message || 'Failed to revoke API key');
    }
  }

  async function handleCreateWebhook(e: React.FormEvent) {
    e.preventDefault();
    if (!webhookUrl.trim()) return;
    try {
      const res = await api.createWebhook(webhookUrl, selectedWebhookEvents);
      setWebhookCreatedSecret(res.secret || null);
      setShowWebhookModal(false);
      setWebhookUrl('');
      loadDeveloperData();
    } catch (err: any) {
      alert(err.message || 'Failed to create webhook endpoint');
    }
  }

  async function handleTestWebhook(id: string) {
    try {
      const res = await api.testWebhook(id);
      alert(`Webhook ping delivered! HTTP Status: ${res.status_code || 200}`);
    } catch (err: any) {
      alert(`Webhook test failed: ${err.message}`);
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/60 backdrop-blur-xl p-6 rounded-2xl border border-slate-800 shadow-xl">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">Developer Portal & Public API v1</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              REST v1.0
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Programmatically integrate Reflow into your workflows, webhooks, and custom SaaS platforms.
          </p>
        </div>
      </div>

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">

        {/* Top Banner */}
        <div className="bg-gradient-to-r from-indigo-900/40 via-purple-900/30 to-slate-900 border border-indigo-500/30 rounded-xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                PUBLIC API V1.0.0
              </span>
              <span className="text-xs text-slate-400">OpenAPI Spec & Client SDKs Ready</span>
            </div>
            <h1 className="text-2xl font-bold text-white mt-1">Reflow Developer Hub</h1>
            <p className="text-sm text-slate-400 mt-1">
              Build custom integrations, automate content workflows with n8n, or manage publications programmatically using scoped API keys and webhooks.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <a
              href="/docs"
              target="_blank"
              rel="noreferrer"
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-sm font-medium transition flex items-center gap-2 border border-slate-700"
            >
              <BookOpen className="w-4 h-4 text-indigo-400" />
              OpenAPI Docs
              <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
            </a>
          </div>
        </div>

        {/* Revealed Key Alert Banner */}
        {rawKeyRevealed && (
          <div className="bg-emerald-950/60 border border-emerald-500/50 rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
                <Shield className="w-5 h-5" />
                API Key Generated — Copy Immediately!
              </div>
              <button onClick={() => setRawKeyRevealed(null)} className="text-xs text-slate-400 hover:text-slate-200">
                Dismiss
              </button>
            </div>
            <p className="text-xs text-slate-300">
              For security, this secret key will never be shown again. Store it securely in your application environment.
            </p>
            <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-700 rounded-lg p-3">
              <code className="text-sm font-mono text-emerald-300 flex-1 break-all">{rawKeyRevealed}</code>
              <button
                onClick={() => copyToClipboard(rawKeyRevealed)}
                className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-semibold flex items-center gap-1.5 transition"
              >
                {copiedKey ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                {copiedKey ? 'Copied' : 'Copy Key'}
              </button>
            </div>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-800 gap-6">
          <button
            onClick={() => setActiveTab('keys')}
            className={`pb-3 text-sm font-medium flex items-center gap-2 border-b-2 transition ${
              activeTab === 'keys'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Key className="w-4 h-4" />
            API Keys ({apiKeys.length})
          </button>
          <button
            onClick={() => setActiveTab('webhooks')}
            className={`pb-3 text-sm font-medium flex items-center gap-2 border-b-2 transition ${
              activeTab === 'webhooks'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Webhook className="w-4 h-4" />
            Webhook Subscriptions ({webhooks.length})
          </button>
          <button
            onClick={() => setActiveTab('sdks')}
            className={`pb-3 text-sm font-medium flex items-center gap-2 border-b-2 transition ${
              activeTab === 'sdks'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Code className="w-4 h-4" />
            SDKs & Code Examples
          </button>
        </div>

        {/* Tab 1: API Keys */}
        {activeTab === 'keys' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-white">Scoped API Keys</h2>
                <p className="text-xs text-slate-400">Generate Bearer tokens for external scripts, AI agents, or n8n nodes with precise scope permissions.</p>
              </div>
              <button
                onClick={() => setShowKeyModal(true)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold flex items-center gap-2 transition shadow-lg shadow-indigo-500/20"
              >
                <Plus className="w-4 h-4" />
                Create New API Key
              </button>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950/60 text-xs uppercase text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="p-4">Key Name</th>
                    <th className="p-4">Prefix</th>
                    <th className="p-4">Assigned Scopes</th>
                    <th className="p-4">Last Used</th>
                    <th className="p-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {apiKeys.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="p-8 text-center text-slate-500">
                        No API keys generated yet. Click &quot;Create New API Key&quot; to get started.
                      </td>
                    </tr>
                  ) : (
                    apiKeys.map((key) => {
                      let scopes: string[] = [];
                      try { scopes = JSON.parse(key.permissions_json || '[]'); } catch {}
                      return (
                        <tr key={key.id} className="hover:bg-slate-800/30 transition">
                          <td className="p-4 font-medium text-white flex items-center gap-2">
                            <Key className="w-4 h-4 text-indigo-400" />
                            {key.name}
                          </td>
                          <td className="p-4">
                            <code className="px-2 py-0.5 bg-slate-800 text-indigo-300 rounded font-mono text-xs">
                              {key.prefix}...
                            </code>
                          </td>
                          <td className="p-4">
                            <div className="flex flex-wrap gap-1">
                              {scopes.slice(0, 4).map((s) => (
                                <span key={s} className="px-2 py-0.5 bg-slate-800 text-slate-300 text-[10px] font-mono rounded border border-slate-700">
                                  {s}
                                </span>
                              ))}
                              {scopes.length > 4 && (
                                <span className="px-1.5 py-0.5 bg-slate-800 text-slate-400 text-[10px] rounded">
                                  +{scopes.length - 4} more
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="p-4 text-xs text-slate-400">
                            {key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : 'Never'}
                          </td>
                          <td className="p-4 text-right">
                            <button
                              onClick={() => handleRevokeKey(key.id)}
                              className="px-2.5 py-1 text-rose-400 hover:bg-rose-950/40 border border-rose-800/40 rounded text-xs transition inline-flex items-center gap-1"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              Revoke
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 2: Webhooks */}
        {activeTab === 'webhooks' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-white">Outbound Webhooks</h2>
                <p className="text-xs text-slate-400">Receive real-time HTTPS callbacks with HMAC-SHA256 signatures when publications finish or jobs complete.</p>
              </div>
              <button
                onClick={() => setShowWebhookModal(true)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold flex items-center gap-2 transition shadow-lg shadow-indigo-500/20"
              >
                <Plus className="w-4 h-4" />
                Add Webhook Endpoint
              </button>
            </div>

            {webhookCreatedSecret && (
              <div className="bg-indigo-950/60 border border-indigo-500/50 rounded-xl p-4 space-y-2">
                <div className="flex items-center justify-between text-indigo-300 font-semibold text-sm">
                  <span>Webhook Signing Secret Created</span>
                  <button onClick={() => setWebhookCreatedSecret(null)} className="text-xs text-slate-400">Dismiss</button>
                </div>
                <p className="text-xs text-slate-300">Use this HMAC secret to verify signature headers (<code className="text-indigo-300">X-Reflow-Signature</code>):</p>
                <code className="block p-2 bg-slate-900 font-mono text-xs text-indigo-400 rounded border border-slate-800">{webhookCreatedSecret}</code>
              </div>
            )}

            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950/60 text-xs uppercase text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="p-4">Endpoint URL</th>
                    <th className="p-4">Subscribed Events</th>
                    <th className="p-4">Status</th>
                    <th className="p-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {webhooks.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="p-8 text-center text-slate-500">
                        No webhook endpoints configured. Click &quot;Add Webhook Endpoint&quot; to subscribe to events.
                      </td>
                    </tr>
                  ) : (
                    webhooks.map((wh) => {
                      let events: string[] = [];
                      try { events = JSON.parse(wh.events_json || '[]'); } catch {}
                      return (
                        <tr key={wh.id} className="hover:bg-slate-800/30 transition">
                          <td className="p-4 font-mono text-xs text-indigo-300 flex items-center gap-2">
                            <Webhook className="w-4 h-4 text-slate-400" />
                            {wh.url}
                          </td>
                          <td className="p-4">
                            <div className="flex flex-wrap gap-1">
                              {events.map((e) => (
                                <span key={e} className="px-2 py-0.5 bg-slate-800 text-slate-300 text-[10px] font-mono rounded">
                                  {e}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="p-4">
                            <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-full ${
                              wh.enabled ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'
                            }`}>
                              {wh.enabled ? 'ACTIVE' : 'DISABLED'}
                            </span>
                          </td>
                          <td className="p-4 text-right space-x-2">
                            <button
                              onClick={() => handleTestWebhook(wh.id)}
                              className="px-2.5 py-1 text-indigo-400 hover:bg-indigo-950/40 border border-indigo-800/40 rounded text-xs transition inline-flex items-center gap-1"
                            >
                              <Send className="w-3.5 h-3.5" />
                              Test Ping
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 3: SDKs & Code Snippets */}
        {activeTab === 'sdks' && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-white">SDK Quickstarts & Code Examples</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Python SDK Box */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-white flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-indigo-400" />
                    Python SDK (reflow-sdk)
                  </h3>
                  <span className="px-2 py-0.5 bg-slate-800 text-indigo-400 text-xs rounded font-mono">v1.0.0</span>
                </div>
                <p className="text-xs text-slate-400">Install via pip and instantiate the ReflowClient with your API key.</p>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-xs text-slate-300 space-y-2 overflow-x-auto">
                  <div className="text-slate-500"># pip install reflow-sdk</div>
                  <div>from reflow import ReflowClient</div>
                  <br />
                  <div>client = ReflowClient(api_key=&quot;reflow_live_...&quot;)</div>
                  <div>content = client.content.create_text(title=&quot;AI Post&quot;, raw_text=&quot;Hello world&quot;)</div>
                  <div>job = client.clips.discover(content[&quot;id&quot;])</div>
                  <div>res = client.jobs.wait(job[&quot;job_id&quot;])</div>
                </div>
              </div>

              {/* TypeScript SDK Box */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-white flex items-center gap-2">
                    <Code className="w-4 h-4 text-purple-400" />
                    TypeScript SDK (@reflow/sdk)
                  </h3>
                  <span className="px-2 py-0.5 bg-slate-800 text-purple-400 text-xs rounded font-mono">v1.0.0</span>
                </div>
                <p className="text-xs text-slate-400">Install via npm/pnpm and interact with strongly typed endpoints.</p>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-xs text-slate-300 space-y-2 overflow-x-auto">
                  <div className="text-slate-500">// npm install @reflow/sdk</div>
                  <div>import &#123; ReflowClient &#125; from &apos;@reflow/sdk&apos;;</div>
                  <br />
                  <div>const client = new ReflowClient(&#123; apiKey: &apos;reflow_live_...&apos; &#125;);</div>
                  <div>const pub = await client.publications.create(&#123;</div>
                  <div>  content_id: &apos;cnt_123&apos;, platform: &apos;INSTAGRAM&apos;, post_type: &apos;REEL&apos;, caption: &apos;Reflow post&apos;</div>
                  <div>&#125;);</div>
                </div>
              </div>
            </div>

            {/* cURL & n8n Section */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
              <h3 className="font-semibold text-white flex items-center gap-2">
                <Terminal className="w-4 h-4 text-emerald-400" />
                cURL & n8n HTTP Request Node Example
              </h3>
              <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 font-mono text-xs text-emerald-300 overflow-x-auto">
                curl -X POST http://localhost:8000/api/v1/content/text \<br />
                &nbsp;&nbsp;-H &quot;Authorization: Bearer reflow_live_your_key_here&quot; \<br />
                &nbsp;&nbsp;-H &quot;Idempotency-Key: req_uniq_12345&quot; \<br />
                &nbsp;&nbsp;-F &quot;title=Automated Ingest&quot; \<br />
                &nbsp;&nbsp;-F &quot;raw_text=Ingested from n8n webhook workflow.&quot;
              </div>
            </div>
          </div>
        )}

      </main>

      {/* Modal: Create API Key */}
      {showKeyModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Key className="w-5 h-5 text-indigo-400" />
              Generate Scoped API Key
            </h3>

            <form onSubmit={handleCreateKey} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Key Name / Description</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. n8n Automation Worker, AI Agent Key"
                  value={keyName}
                  onChange={(e) => setKeyName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-2">Scope Permissions (Least Privilege)</label>
                <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto p-2 bg-slate-950 rounded-lg border border-slate-800">
                  {ALL_SCOPES.map((s) => (
                    <label key={s} className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer hover:text-white">
                      <input
                        type="checkbox"
                        checked={selectedScopes.includes(s)}
                        onChange={(e) => {
                          if (e.target.checked) setSelectedScopes([...selectedScopes, s]);
                          else setSelectedScopes(selectedScopes.filter((x) => x !== s));
                        }}
                        className="rounded border-slate-700 text-indigo-600 focus:ring-0"
                      />
                      {s}
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowKeyModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow-lg shadow-indigo-500/20"
                >
                  Generate Key
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Create Webhook */}
      {showWebhookModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Webhook className="w-5 h-5 text-indigo-400" />
              Subscribe Webhook Endpoint
            </h3>

            <form onSubmit={handleCreateWebhook} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">HTTPS Callback URL</label>
                <input
                  type="url"
                  required
                  placeholder="https://your-server.com/api/reflow-webhook"
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowWebhookModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow-lg shadow-indigo-500/20"
                >
                  Subscribe Endpoint
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
