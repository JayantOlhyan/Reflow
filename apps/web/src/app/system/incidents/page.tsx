"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  AlertTriangle, 
  ShieldAlert, 
  CheckCircle2, 
  Clock, 
  UserCheck, 
  FileText, 
  ArrowLeft,
  RefreshCw,
  Search,
  Filter,
  Check,
  ChevronRight
} from 'lucide-react';
import { SystemIncidentItem } from '@/types';
import { api } from '@/lib/api';

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<SystemIncidentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');

  // Modal State
  const [selectedIncident, setSelectedIncident] = useState<SystemIncidentItem | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Operator Action Modals
  const [ackModalOpen, setAckModalOpen] = useState(false);
  const [operatorName, setOperatorName] = useState('Operator');
  
  const [resolveModalOpen, setResolveModalOpen] = useState(false);
  const [resolutionNote, setResolutionNote] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadIncidents = async () => {
    try {
      setLoading(true);
      const data = await api.getIncidents({
        status: statusFilter === 'ALL' ? undefined : statusFilter,
        severity: severityFilter === 'ALL' ? undefined : severityFilter
      });
      setIncidents(data);
    } catch (err) {
      console.warn("Failed to load incidents:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIncidents();
  }, [statusFilter, severityFilter]);

  const handleOpenDetail = async (inc: SystemIncidentItem) => {
    try {
      setDetailLoading(true);
      const detail = await api.getIncidentDetail(inc.id);
      setSelectedIncident(detail);
    } catch (err) {
      setSelectedIncident(inc);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleAcknowledge = async () => {
    if (!selectedIncident) return;
    try {
      setSubmitting(true);
      await api.acknowledgeIncident(selectedIncident.id, operatorName);
      setAckModalOpen(false);
      await handleOpenDetail(selectedIncident);
      await loadIncidents();
    } catch (err) {
      alert(`Acknowledgement failed: ${err}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleResolve = async () => {
    if (!selectedIncident) return;
    if (!resolutionNote.trim() || resolutionNote.trim().length < 5) {
      alert("Resolution explanation must be at least 5 characters long.");
      return;
    }
    try {
      setSubmitting(true);
      await api.resolveIncident(selectedIncident.id, resolutionNote);
      setResolveModalOpen(false);
      setResolutionNote('');
      await handleOpenDetail(selectedIncident);
      await loadIncidents();
    } catch (err) {
      alert(`Resolution failed: ${err}`);
    } finally {
      setSubmitting(false);
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'HIGH':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/30';
      case 'MEDIUM':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
      case 'LOW':
        return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30';
      default:
        return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case 'OPEN':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/30 animate-pulse';
      case 'INVESTIGATING':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
      case 'RESOLVED':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
      case 'CLOSED':
      default:
        return 'bg-gray-700/30 text-gray-400 border-gray-600';
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Top Header Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            href="/system"
            className="p-2 text-gray-400 hover:text-white rounded-xl bg-[#111827] border border-[#1F2937] hover:bg-[#161B26] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">System Incident Hub</h1>
            <p className="text-xs text-gray-400 mt-0.5">Deduplicated operational incidents, operator acknowledgements, and timeline audit logs.</p>
          </div>
        </div>

        <button
          onClick={loadIncidents}
          className="p-2 text-gray-400 hover:text-white rounded-xl bg-[#111827] border border-[#1F2937] hover:bg-[#161B26] transition-colors self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Filter Tabs & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#111827] p-3 rounded-2xl border border-[#1F2937]">
        <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0">
          {['ALL', 'OPEN', 'INVESTIGATING', 'RESOLVED', 'CLOSED'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                statusFilter === st
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-gray-400" />
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-[#161B26] border border-[#1F2937] text-gray-300 text-xs rounded-xl px-3 py-1.5 focus:outline-none focus:border-indigo-500 font-semibold"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </div>
      </div>

      {/* Main Grid: Incident List + Selected Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Incident List Column */}
        <div className="lg:col-span-5 space-y-3">
          {loading ? (
            <div className="p-8 text-center text-xs text-gray-500 bg-[#111827] border border-[#1F2937] rounded-2xl">
              Loading incidents...
            </div>
          ) : incidents.length === 0 ? (
            <div className="p-12 text-center text-xs text-gray-500 bg-[#111827] border border-[#1F2937] rounded-2xl">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
              <p className="font-semibold text-gray-300">No Incidents Found</p>
              <p className="text-[11px] text-gray-500">No operational incidents match your active filters.</p>
            </div>
          ) : (
            incidents.map((inc) => (
              <div
                key={inc.id}
                onClick={() => handleOpenDetail(inc)}
                className={`p-4 bg-[#111827] border rounded-2xl cursor-pointer transition-all ${
                  selectedIncident?.id === inc.id
                    ? 'border-indigo-500 shadow-md bg-[#161B26]'
                    : 'border-[#1F2937] hover:border-gray-700'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 border text-[10px] font-bold rounded ${getSeverityBadge(inc.severity)}`}>
                      {inc.severity}
                    </span>
                    <span className={`px-2 py-0.5 border text-[10px] font-bold rounded ${getStatusBadge(inc.status)}`}>
                      {inc.status}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-gray-500">{inc.started_at.split('T')[0]}</span>
                </div>

                <h3 className="text-xs font-bold text-white mb-1 line-clamp-1">{inc.title}</h3>
                <p className="text-xs text-gray-400 line-clamp-2">{inc.description}</p>
                
                <div className="mt-3 flex items-center justify-between text-[11px] text-gray-500 pt-2 border-t border-[#1F2937]">
                  <span>Component: <strong className="text-gray-300">{inc.component}</strong></span>
                  <ChevronRight className="w-3.5 h-3.5 text-gray-500" />
                </div>
              </div>
            ))
          )}
        </div>

        {/* Selected Incident Detail Column */}
        <div className="lg:col-span-7">
          {!selectedIncident ? (
            <div className="p-12 text-center text-xs text-gray-500 bg-[#111827] border border-[#1F2937] rounded-2xl h-full flex flex-col items-center justify-center">
              <ShieldAlert className="w-10 h-10 text-gray-600 mb-3" />
              <p className="font-semibold text-gray-300">Select an Incident to Inspect</p>
              <p className="text-[11px] text-gray-500">Choose an incident from the list to view affected resources, timeline events, and operator mitigation controls.</p>
            </div>
          ) : (
            <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 space-y-6">
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#1F2937]">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2.5 py-0.5 border text-xs font-bold rounded ${getSeverityBadge(selectedIncident.severity)}`}>
                      {selectedIncident.severity}
                    </span>
                    <span className={`px-2.5 py-0.5 border text-xs font-bold rounded ${getStatusBadge(selectedIncident.status)}`}>
                      {selectedIncident.status}
                    </span>
                    <span className="text-xs font-mono text-gray-500">#{selectedIncident.id}</span>
                  </div>
                  <h2 className="text-base font-bold text-white">{selectedIncident.title}</h2>
                </div>

                <div className="flex items-center gap-2">
                  {selectedIncident.status === 'OPEN' && (
                    <button
                      onClick={() => setAckModalOpen(true)}
                      className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs rounded-xl flex items-center gap-1.5 transition-colors"
                    >
                      <UserCheck className="w-3.5 h-3.5" />
                      <span>Acknowledge</span>
                    </button>
                  )}

                  {selectedIncident.status !== 'RESOLVED' && selectedIncident.status !== 'CLOSED' && (
                    <button
                      onClick={() => setResolveModalOpen(true)}
                      className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs rounded-xl flex items-center gap-1.5 transition-colors"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Resolve</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Description & Component Info */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">Incident Overview</h4>
                <p className="text-xs text-gray-300 bg-[#161B26] p-3 rounded-xl border border-[#1F2937] leading-relaxed">
                  {selectedIncident.description}
                </p>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="bg-[#161B26] p-3 rounded-xl border border-[#1F2937]">
                    <span className="text-gray-500 text-[11px]">Component</span>
                    <p className="font-bold text-white mt-0.5">{selectedIncident.component}</p>
                  </div>
                  <div className="bg-[#161B26] p-3 rounded-xl border border-[#1F2937]">
                    <span className="text-gray-500 text-[11px]">Error Code</span>
                    <p className="font-bold text-indigo-300 font-mono mt-0.5">{selectedIncident.error_code || 'N/A'}</p>
                  </div>
                </div>
              </div>

              {/* Resolution Note display if resolved */}
              {selectedIncident.resolution_note && (
                <div className="bg-emerald-500/10 border border-emerald-500/30 p-4 rounded-xl space-y-1">
                  <span className="text-xs font-bold text-emerald-300 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4" />
                    Resolution Note
                  </span>
                  <p className="text-xs text-emerald-200">{selectedIncident.resolution_note}</p>
                </div>
              )}

              {/* Affected Resources */}
              {selectedIncident.affected_resources && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">Affected Resources</h4>
                  <div className="bg-[#161B26] p-3 rounded-xl border border-[#1F2937] text-xs font-mono space-y-1 text-gray-300">
                    <p>Affected Jobs: <span className="text-indigo-400">{selectedIncident.affected_resources.affected_jobs?.length || 0}</span></p>
                    <p>Affected Content: <span className="text-indigo-400">{selectedIncident.affected_resources.affected_content?.length || 0}</span></p>
                    <p>Recurrence Count: <span className="text-indigo-400">{selectedIncident.affected_resources.failure_count || 1}</span></p>
                  </div>
                </div>
              )}

              {/* Incident Timeline */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">Incident Timeline Audit</h4>
                {selectedIncident.timeline && selectedIncident.timeline.length > 0 ? (
                  <div className="space-y-2">
                    {selectedIncident.timeline.map((evt) => (
                      <div key={evt.id} className="p-3 bg-[#161B26] rounded-xl border border-[#1F2937] text-xs flex items-start gap-3">
                        <Clock className="w-3.5 h-3.5 text-indigo-400 mt-0.5 shrink-0" />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-white">{evt.event_type}</span>
                            <span className="text-[10px] text-gray-500">{evt.created_at}</span>
                          </div>
                          <p className="text-gray-400 mt-0.5">{evt.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-500">No timeline events recorded.</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Operator Acknowledge Modal */}
      {ackModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 max-w-md w-full space-y-4">
            <h3 className="text-base font-bold text-white">Acknowledge Incident</h3>
            <p className="text-xs text-gray-400">Mark incident as INVESTIGATING and assign operator responsibility.</p>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-300">Operator Name / ID</label>
              <input
                type="text"
                value={operatorName}
                onChange={(e) => setOperatorName(e.target.value)}
                className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setAckModalOpen(false)}
                className="px-4 py-2 bg-[#161B26] hover:bg-[#1F2937] text-gray-300 text-xs font-semibold rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleAcknowledge}
                disabled={submitting}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold rounded-xl disabled:opacity-50"
              >
                {submitting ? 'Updating...' : 'Confirm Acknowledge'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Operator Resolve Modal */}
      {resolveModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 max-w-md w-full space-y-4">
            <h3 className="text-base font-bold text-white">Resolve Incident</h3>
            <p className="text-xs text-gray-400">Provide an explicit resolution explanation note before closing this incident.</p>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-300">Resolution Explanation Note *</label>
              <textarea
                value={resolutionNote}
                onChange={(e) => setResolutionNote(e.target.value)}
                placeholder="Explain the root cause fix, mitigation steps applied, or underlying issue recovery..."
                rows={4}
                className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl p-3 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setResolveModalOpen(false)}
                className="px-4 py-2 bg-[#161B26] hover:bg-[#1F2937] text-gray-300 text-xs font-semibold rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleResolve}
                disabled={submitting}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl disabled:opacity-50"
              >
                {submitting ? 'Resolving...' : 'Confirm Resolution'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
