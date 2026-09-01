"use client";

import React, { useState, useEffect } from 'react';
import { 
  Webhook, 
  Plus, 
  Trash2, 
  Send, 
  CheckCircle2, 
  XCircle, 
  RefreshCw, 
  ShieldCheck,
  Clock,
  ExternalLink
} from 'lucide-react';
import { WebhookItem } from '@/types';
import { api } from '@/lib/api';

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState<WebhookItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  
  // Form State
  const [targetUrl, setTargetUrl] = useState<string>('');
  const [selectedEvents, setSelectedEvents] = useState<string[]>([
    'content.ready', 'publication.succeeded', 'publication.failed'
  ]);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  const availableEvents = [
    { id: 'content.created', label: 'content.created — New source uploaded' },
    { id: 'content.ready', label: 'content.ready — Audio/transcript processing ready' },
    { id: 'clip.ready', label: 'clip.ready — Short-form clip discovered & extracted' },
    { id: 'carousel.ready', label: 'carousel.ready — Slide deck generated' },
    { id: 'publication.succeeded', label: 'publication.succeeded — Published to social platform' },
    { id: 'publication.failed', label: 'publication.failed — Platform publish error' },
    { id: 'analytics.updated', label: 'analytics.updated — Analytics snapshot updated' },
    { id: 'experiment.completed', label: 'experiment.completed — A/B experiment concluded' },
    { id: 'automation.completed', label: 'automation.completed — Automation workflow finished' },
    { id: 'governance.blocked', label: 'governance.blocked — Publication blocked by policy' },
  ];

  useEffect(() => {
    loadWebhooks();
  }, []);

  const loadWebhooks = async () => {
    try {
      setLoading(true);
      const res = await api.getWebhooks();
      setWebhooks(res || []);
    } catch (e) {
      console.warn("Failed to load webhooks:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetUrl.trim()) return;
    try {
      setIsSubmitting(true);
      await api.createWebhook(targetUrl.trim(), selectedEvents);
      setIsModalOpen(false);
      setTargetUrl('');
      await loadWebhooks();
    } catch (err: any) {
      alert(`Failed to create webhook: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this webhook endpoint?")) return;
    try {
      await api.deleteWebhook(id);
      await loadWebhooks();
    } catch (e: any) {
      alert(`Delete failed: ${e.message}`);
    }
  };

  const handleTestDelivery = async (id: string) => {
    try {
      setTestResult("Testing delivery...");
      const res = await api.testWebhook(id);
      setTestResult(`Delivery Result: ${JSON.stringify(res)}`);
      await loadWebhooks();
    } catch (e: any) {
      setTestResult(`Test delivery failed: ${e.message}`);
    }
  };

  const toggleEvent = (eventId: string) => {
    setSelectedEvents(prev => 
      prev.includes(eventId) ? prev.filter(e => e !== eventId) : [...prev, eventId]
    );
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Webhook className="w-6 h-6 text-indigo-400" />
            <h1 className="text-2xl font-bold text-white tracking-tight">Outbound Webhooks</h1>
          </div>
          <p className="text-xs text-slate-400">
            Configure signed HTTP webhook endpoints (HMAC-SHA256) for real-time Reflow lifecycle event delivery.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-lg shadow-indigo-600/20"
        >
          <Plus className="w-4 h-4" />
          <span>Add Webhook Endpoint</span>
        </button>
      </div>

      {testResult && (
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-300 font-mono">
          {testResult}
        </div>
      )}

      {/* Webhooks List */}
      {loading ? (
        <div className="py-20 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
          <span>Loading webhook endpoints...</span>
        </div>
      ) : webhooks.length === 0 ? (
        <div className="py-16 text-center bg-slate-900/50 border border-dashed border-slate-800 rounded-2xl p-8 space-y-3">
          <Webhook className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-sm font-semibold text-white">No Webhook Endpoints Configured</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Add an HTTPS target URL to receive real-time signed payload notifications when content is processed or published.
          </p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-xs font-semibold inline-flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create First Webhook</span>
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {webhooks.map((wh) => (
            <div key={wh.id} className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-lg">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-white bg-slate-800 px-2 py-0.5 rounded">{wh.id}</span>
                    <span className="text-xs font-mono text-indigo-300 font-semibold truncate max-w-md">{wh.url}</span>
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-slate-500 font-mono pt-1">
                    <span>Created: {new Date(wh.created_at).toLocaleDateString()}</span>
                    {wh.last_success_at && (
                      <span className="text-emerald-400">Last Success: {new Date(wh.last_success_at).toLocaleTimeString()}</span>
                    )}
                    {wh.last_failure_at && (
                      <span className="text-rose-400">Last Failure: {new Date(wh.last_failure_at).toLocaleTimeString()}</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleTestDelivery(wh.id)}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-750 text-indigo-300 rounded-xl text-xs font-semibold flex items-center gap-1 border border-slate-700"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Test Delivery</span>
                  </button>

                  <button
                    onClick={() => handleDelete(wh.id)}
                    className="p-1.5 bg-slate-800 hover:bg-rose-600/20 text-slate-400 hover:text-rose-400 border border-slate-700 rounded-xl transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Subscribed Event Badges */}
              <div className="pt-2 border-t border-slate-800/80 flex items-center gap-1.5 flex-wrap">
                <span className="text-[10px] text-slate-500 font-mono">Events:</span>
                {wh.events.map((evt) => (
                  <span key={evt} className="px-2 py-0.5 bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 rounded text-[10px] font-mono">
                    {evt}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* CREATE WEBHOOK MODAL */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-lg space-y-4 shadow-2xl">
            <h2 className="text-base font-bold text-white">Add Webhook Endpoint</h2>
            <form onSubmit={handleCreateWebhook} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Target Webhook URL</label>
                <input
                  type="url"
                  required
                  value={targetUrl}
                  onChange={(e) => setTargetUrl(e.target.value)}
                  placeholder="https://your-domain.com/webhooks/reflow"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-2">Subscribed Event Topics</label>
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {availableEvents.map((evt) => (
                    <label key={evt.id} className="flex items-center space-x-2 text-xs text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedEvents.includes(evt.id)}
                        onChange={() => toggleEvent(evt.id)}
                        className="rounded bg-slate-800 border-slate-700 text-indigo-600 focus:ring-0"
                      />
                      <span>{evt.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 text-slate-400 rounded-xl text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold"
                >
                  {isSubmitting ? "Saving..." : "Create Endpoint"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
