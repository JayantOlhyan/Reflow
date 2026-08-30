"use client";

import React, { useState, useEffect } from 'react';
import { 
  Experiment, ExperimentVariant, ExperimentResult, ExperimentWarning, ExperimentDetailResponse
} from '@/types';
import { api } from '@/lib/api';
import { 
  Beaker, Play, Plus, RefreshCw, AlertTriangle, CheckCircle, XCircle, ArrowRight, Download, HelpCircle, FileText, Database
} from 'lucide-react';

export default function ExperimentsPage() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedExp, setSelectedExp] = useState<ExperimentDetailResponse | null>(null);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [creating, setCreating] = useState(false);
  const [refreshing, setRefreshing] = useState<string | null>(null);
  const [starting, setStarting] = useState<string | null>(null);

  // Content list for wizard selection
  const [contents, setContents] = useState<any[]>([]);

  // Form State for Creation Wizard
  const [showWizard, setShowWizard] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    hypothesis: '',
    scope: 'HOOK',
    platform: 'linkedin',
    primary_metric: 'engagement_rate',
    control_content_id: '',
    treatment_content_id: '',
    control_variant_id: '',
    treatment_variant_id: '',
    control_publication_id: '',
    treatment_publication_id: '',
    minimum_sample_size: 5,
    confidence_level: 0.95,
    secondary_metrics: [] as string[]
  });
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Load experiments
  const loadExperiments = async () => {
    try {
      setLoadingList(true);
      const list = await api.getExperimentsList();
      setExperiments(list);
    } catch (err: any) {
      console.error("Failed to load experiments:", err);
    } finally {
      setLoadingList(false);
    }
  };

  // Load contents for wizard dropdown
  const loadContents = async () => {
    try {
      const res = await api.getContentList({ limit: 100 });
      setContents(res.items || []);
    } catch (err) {
      console.error("Failed to load contents:", err);
    }
  };

  useEffect(() => {
    loadExperiments();
    loadContents();
  }, []);

  // View Details
  const handleViewDetails = async (id: string) => {
    try {
      setLoadingDetails(true);
      setErrorMsg(null);
      const details = await api.getExperimentDetails(id);
      setSelectedExp(details);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load experiment details.");
    } finally {
      setLoadingDetails(false);
    }
  };

  // Start Experiment
  const handleStartExperiment = async (id: string) => {
    try {
      setStarting(id);
      setErrorMsg(null);
      const updated = await api.startExperiment(id);
      setSelectedExp(updated);
      await loadExperiments();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to start experiment.");
    } finally {
      setStarting(null);
    }
  };

  // Refresh/Trigger sweep
  const handleRefreshExperiment = async (id: string) => {
    try {
      setRefreshing(id);
      setErrorMsg(null);
      await api.refreshExperiment(id);
      // Wait a moment for worker and reload details
      setTimeout(async () => {
        const updated = await api.getExperimentDetails(id);
        setSelectedExp(updated);
        await loadExperiments();
        setRefreshing(null);
      }, 1500);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to enqueue evaluation job.");
      setRefreshing(null);
    }
  };

  // Create Experiment Submit
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setCreating(true);
      setErrorMsg(null);

      if (!formData.name || !formData.hypothesis || !formData.control_content_id || !formData.treatment_content_id) {
        throw new Error("Please fill in all required fields.");
      }

      const res = await api.createExperiment(formData);
      setShowWizard(false);
      setSelectedExp(res);
      await loadExperiments();

      // Reset form
      setFormData({
        name: '',
        hypothesis: '',
        scope: 'HOOK',
        platform: 'linkedin',
        primary_metric: 'engagement_rate',
        control_content_id: '',
        treatment_content_id: '',
        control_variant_id: '',
        treatment_variant_id: '',
        control_publication_id: '',
        treatment_publication_id: '',
        minimum_sample_size: 5,
        confidence_level: 0.95,
        secondary_metrics: []
      });
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to create experiment.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6 pb-12 text-gray-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Beaker className="w-6 h-6 text-indigo-400" />
            Content Experimentation Hub
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            Design controlled A/B tests, measure content hypotheses, and calculate statistical confidence.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <a
            href={api.exportExperimentsCsvUrl()}
            download="experiments_export.csv"
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-gray-400 hover:text-white bg-[#111827] border border-[#1F2937] hover:bg-[#161B26] rounded-xl transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            Export CSV
          </a>

          <button
            onClick={() => setShowWizard(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl shadow-sm transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            New Experiment
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 px-4 py-3 rounded-xl text-xs flex items-center gap-2">
          <XCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Grid: Main Dashboard & Details Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Col: Experiments List */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-4">
            <h2 className="text-sm font-semibold text-white mb-3">Experiments</h2>

            {loadingList ? (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className="w-5 h-5 text-gray-500 animate-spin" />
              </div>
            ) : experiments.length === 0 ? (
              <div className="text-center py-12 border-2 border-dashed border-[#1F2937] rounded-lg">
                <Beaker className="w-8 h-8 text-gray-600 mx-auto mb-2" />
                <p className="text-xs text-gray-400">No experiments defined yet.</p>
                <button
                  onClick={() => setShowWizard(true)}
                  className="mt-3 text-xs text-indigo-400 hover:underline font-semibold"
                >
                  Create one now
                </button>
              </div>
            ) : (
              <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
                {experiments.map((exp) => (
                  <button
                    key={exp.id}
                    onClick={() => handleViewDetails(exp.id)}
                    className={`w-full text-left p-3 rounded-lg border transition-all ${
                      selectedExp?.experiment.id === exp.id
                        ? 'bg-indigo-600/10 border-indigo-500/40 text-white'
                        : 'bg-[#161B26]/40 border-[#1F2937] hover:border-gray-700 hover:bg-[#161B26]/80'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="text-xs font-semibold truncate text-white">{exp.name}</h3>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium shrink-0 ${
                        exp.status === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                        exp.status === 'RUNNING' ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' :
                        exp.status === 'INSUFFICIENT_DATA' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                        'bg-gray-500/10 text-gray-400 border border-gray-500/20'
                      }`}>
                        {exp.status}
                      </span>
                    </div>
                    <p className="text-[10px] text-gray-400 line-clamp-2 mt-1">{exp.hypothesis}</p>
                    
                    <div className="flex items-center justify-between text-[9px] text-gray-500 mt-2.5 pt-2 border-t border-[#1f2937]/50">
                      <span>Scope: {exp.scope}</span>
                      <span className="capitalize">{exp.platform}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Col: Detail & Evaluation Scorecard */}
        <div className="lg:col-span-2 space-y-6">
          {loadingDetails ? (
            <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-8 flex items-center justify-center min-h-[400px]">
              <RefreshCw className="w-6 h-6 text-gray-500 animate-spin" />
            </div>
          ) : selectedExp ? (
            <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-6 space-y-6">
              {/* Detail Header */}
              <div className="flex items-start justify-between gap-4 border-b border-[#1F2937] pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-[#161B26] border border-[#1F2937] text-gray-400 capitalize">
                      {selectedExp.experiment.platform}
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-[#161B26] border border-[#1F2937] text-gray-400">
                      Scope: {selectedExp.experiment.scope}
                    </span>
                  </div>
                  <h2 className="text-base font-bold text-white mt-2">{selectedExp.experiment.name}</h2>
                  <p className="text-xs text-indigo-400 mt-1 italic">
                    Hypothesis: "{selectedExp.experiment.hypothesis}"
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {selectedExp.experiment.status === 'DRAFT' && (
                    <button
                      onClick={() => handleStartExperiment(selectedExp.experiment.id)}
                      disabled={starting === selectedExp.experiment.id}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-xl transition-colors"
                    >
                      {starting === selectedExp.experiment.id ? (
                        <RefreshCw className="w-3 h-3 animate-spin" />
                      ) : (
                        <Play className="w-3 h-3" />
                      )}
                      Start Test
                    </button>
                  )}

                  {selectedExp.experiment.status === 'RUNNING' && (
                    <button
                      onClick={() => handleRefreshExperiment(selectedExp.experiment.id)}
                      disabled={refreshing === selectedExp.experiment.id}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-gray-300 bg-[#161B26] border border-[#1F2937] hover:bg-[#1f293d] disabled:opacity-50 rounded-xl transition-colors"
                    >
                      <RefreshCw className={`w-3 h-3 ${refreshing === selectedExp.experiment.id ? 'animate-spin' : ''}`} />
                      Refresh Data
                    </button>
                  )}
                </div>
              </div>

              {/* Design Warnings */}
              {selectedExp.warnings && selectedExp.warnings.length > 0 && (
                <div className="bg-amber-500/10 border border-amber-500/20 text-amber-400 p-4 rounded-xl space-y-2">
                  <div className="flex items-center gap-1.5 font-bold text-xs text-amber-300">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    Potential Confounds & Flaws Detected
                  </div>
                  <ul className="list-disc list-inside text-[11px] space-y-1 pl-1">
                    {selectedExp.warnings.map((w, idx) => (
                      <li key={idx}><span className="font-semibold">[{w.code}]</span> {w.message}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Scorecard / Evaluation Results */}
              <div className="space-y-4">
                <h3 className="text-xs font-semibold text-white">Statistical Scorecard</h3>

                {selectedExp.experiment.status === 'DRAFT' ? (
                  <div className="text-center py-12 bg-[#161B26]/30 border border-[#1F2937] rounded-xl">
                    <Play className="w-8 h-8 text-gray-600 mx-auto mb-2" />
                    <p className="text-xs text-white font-medium">Experiment is in Draft</p>
                    <p className="text-[10px] text-gray-500 mt-1 max-w-sm mx-auto">
                      Click the "Start Test" button above to transition it to running and begin evaluating metrics snapshots.
                    </p>
                  </div>
                ) : selectedExp.results.length === 0 ? (
                  <div className="text-center py-12 bg-indigo-950/10 border border-indigo-900/20 text-indigo-400 rounded-xl space-y-2">
                    <Database className="w-8 h-8 mx-auto text-indigo-500" />
                    <p className="text-xs font-bold text-indigo-300">Honest Evaluation: Pending Data Alignment</p>
                    <p className="text-[10px] text-gray-400 max-w-md mx-auto px-4">
                      All control and treatment observations must be evaluated at equivalent times since publish (e.g. 24h window).
                      If publications are younger than the target age, evaluation remains pending to prevent pre-mature age bias.
                    </p>
                    <div className="text-[10px] bg-indigo-950/40 px-3 py-1.5 rounded-lg inline-block text-gray-400">
                      Sample Size: {selectedExp.variants.length} / Min Required: {selectedExp.experiment.minimum_sample_size}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* Scorecard Table */}
                    <div className="overflow-x-auto border border-[#1F2937] rounded-xl bg-[#161B26]/20">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="bg-[#161B26]/50 border-b border-[#1F2937] text-gray-400 font-medium">
                            <th className="p-3">Variant</th>
                            <th className="p-3">Role</th>
                            <th className="p-3">Sample (n)</th>
                            <th className="p-3 capitalize">{selectedExp.experiment.primary_metric.replace('_', ' ')}</th>
                            <th className="p-3">Abs. Effect</th>
                            <th className="p-3">Rel. Effect</th>
                            <th className="p-3">P-Value</th>
                            <th className="p-3 text-center">Sig.</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#1F2937]">
                          {selectedExp.variants.map((v) => {
                            const res = selectedExp.results.find(r => r.variant_id === v.id);
                            return (
                              <tr key={v.id} className="hover:bg-[#161B26]/20 text-gray-300">
                                <td className="p-3 font-semibold text-white">{v.name}</td>
                                <td className="p-3">
                                  <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                                    v.role === 'CONTROL' ? 'bg-gray-500/10 text-gray-400' : 'bg-indigo-500/10 text-indigo-400'
                                  }`}>
                                    {v.role}
                                  </span>
                                </td>
                                <td className="p-3">{res?.sample_size ?? 0}</td>
                                <td className="p-3 font-semibold text-white">
                                  {res?.metric_value !== undefined && res.metric_value !== null
                                    ? selectedExp.experiment.primary_metric.endsWith('rate')
                                      ? `${(res.metric_value * 100).toFixed(2)}%`
                                      : res.metric_value.toFixed(0)
                                    : 'Pending'}
                                </td>
                                <td className="p-3">
                                  {res?.abs_effect_size !== undefined && res.abs_effect_size !== null
                                    ? selectedExp.experiment.primary_metric.endsWith('rate')
                                      ? `${(res.abs_effect_size * 100).toFixed(2)}%`
                                      : res.abs_effect_size.toFixed(1)
                                    : '-'}
                                </td>
                                <td className="p-3">
                                  {res?.rel_effect_size !== undefined && res.rel_effect_size !== null
                                    ? `${(res.rel_effect_size * 100).toFixed(1)}%`
                                    : res?.rel_effect_size === null ? 'N/A (Control = 0)' : '-'}
                                </td>
                                <td className="p-3">
                                  {res?.p_value !== undefined && res.p_value !== null
                                    ? res.p_value.toFixed(4)
                                    : '-'}
                                </td>
                                <td className="p-3 text-center">
                                  {res ? (
                                    res.statistical_significance ? (
                                      <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                                        <CheckCircle className="w-2.5 h-2.5" /> Sig
                                      </span>
                                    ) : (
                                      <span className="inline-flex items-center gap-0.5 text-[10px] text-gray-400 bg-gray-500/10 px-1.5 py-0.5 rounded">
                                        No Sig
                                      </span>
                                    )
                                  ) : '-'}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>

                    {/* Winner / conclusion declaration panel */}
                    <div className="bg-indigo-950/20 border border-indigo-900/30 p-5 rounded-xl space-y-3">
                      <h4 className="text-xs font-bold text-white flex items-center gap-1">
                        <Beaker className="w-4 h-4 text-indigo-400" />
                        Statistical Conclusion
                      </h4>

                      <div className="text-xs space-y-1 text-gray-300">
                        <p>
                          <span className="font-semibold text-white">Status:</span>{' '}
                          <span className="capitalize">{selectedExp.experiment.status.replace('_', ' ')}</span>
                        </p>
                        {selectedExp.experiment.conclusion && (
                          <p>
                            <span className="font-semibold text-white">Evidence Summary:</span>{' '}
                            <span className="text-indigo-300">{selectedExp.experiment.conclusion}</span>
                          </p>
                        )}
                      </div>

                      {selectedExp.experiment.status === 'COMPLETED' && selectedExp.experiment.winner_variant_id && (
                        <div className="flex items-center gap-2 p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg text-xs">
                          <CheckCircle className="w-4 h-4 shrink-0 animate-pulse" />
                          <div>
                            <span className="font-bold">Hypothesis Validated!</span> Variant{' '}
                            <span className="font-bold underline">
                              {selectedExp.variants.find(v => v.id === selectedExp.experiment.winner_variant_id)?.name}
                            </span>{' '}
                            declared the winner with statistical significance (p &lt; {1 - selectedExp.experiment.confidence_level}).
                          </div>
                        </div>
                      )}

                      {selectedExp.experiment.status === 'COMPLETED' && !selectedExp.experiment.winner_variant_id && (
                        <div className="flex items-center gap-2 p-3 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg text-xs">
                          <HelpCircle className="w-4 h-4 shrink-0" />
                          <div>
                            <span className="font-bold">Inconclusive Result.</span> The statistical confidence did not cross the threshold.
                            No clear winner could be declared under current sample sizes.
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-8 text-center flex flex-col items-center justify-center min-h-[400px]">
              <Beaker className="w-12 h-12 text-gray-700 mb-3" />
              <h3 className="text-sm font-semibold text-white">No Experiment Selected</h3>
              <p className="text-xs text-gray-500 mt-1 max-w-sm">
                Select an experiment from the left pane to view its design warnings, scorecard, and statistical conclusions.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Creation Wizard Dialog Modal */}
      {showWizard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[#111827] border border-[#1F2937] rounded-xl max-w-lg w-full max-h-[90vh] overflow-y-auto shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-[#1F2937] pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                <Beaker className="w-4 h-4 text-indigo-400" />
                A/B Testing Wizard
              </h3>
              <button
                onClick={() => setShowWizard(false)}
                className="text-xs text-gray-500 hover:text-white"
              >
                Close
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs">
              <div className="space-y-1">
                <label className="block text-gray-400 font-semibold">Experiment Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. LinkedIn Hook Variant A/B Test"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full bg-[#161B26] border border-[#1F2937] rounded-lg p-2.5 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-gray-400 font-semibold">Hypothesis * (Min. 5 chars)</label>
                <textarea
                  required
                  rows={2}
                  placeholder="e.g. Statistic-heavy hooks produce 15% higher engagement rates than generic questions."
                  value={formData.hypothesis}
                  onChange={(e) => setFormData({ ...formData, hypothesis: e.target.value })}
                  className="w-full bg-[#161B26] border border-[#1F2937] rounded-lg p-2.5 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="block text-gray-400 font-semibold">Scope</label>
                  <select
                    value={formData.scope}
                    onChange={(e: any) => setFormData({ ...formData, scope: e.target.value })}
                    className="w-full bg-[#161B26] border border-[#1F2937] rounded-lg p-2.5 text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="HOOK">HOOK (Caption Hook Line)</option>
                    <option value="CAPTION">CAPTION (Entire Caption Body)</option>
                    <option value="THUMBNAIL">THUMBNAIL (Cover Image)</option>
                    <option value="TITLE">TITLE (Video Title)</option>
                    <option value="CTA">CTA (Call-to-Action Text)</option>
                    <option value="DURATION">DURATION (Short-form vs Long)</option>
                    <option value="FORMAT">FORMAT (Video vs Carousel)</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="block text-gray-400 font-semibold">Platform</label>
                  <select
                    value={formData.platform}
                    onChange={(e) => setFormData({ ...formData, platform: e.target.value })}
                    className="w-full bg-[#161B26] border border-[#1F2937] rounded-lg p-2.5 text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="linkedin">LinkedIn</option>
                    <option value="youtube">YouTube</option>
                    <option value="instagram">Instagram</option>
                    <option value="facebook">Facebook</option>
                    <option value="x">X (Twitter)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="block text-gray-400 font-semibold">Primary Metric</label>
                  <select
                    value={formData.primary_metric}
                    onChange={(e) => setFormData({ ...formData, primary_metric: e.target.value })}
                    className="w-full bg-[#161B26] border border-[#1F2937] rounded-lg p-2.5 text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="engagement_rate">Engagement Rate (%)</option>
                    <option value="views">Views (Count)</option>
                    <option value="completion_rate">Completion Rate (%)</option>
                    <option value="click_rate">Click Rate (%)</option>
                    <option value="likes">Likes (Count)</option>
                    <option value="comments">Comments (Count)</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="block text-gray-400 font-semibold">Min Sample Size (posts)</label>
                  <input
                    type="number"
                    min={2}
                    value={formData.minimum_sample_size}
                    onChange={(e) => setFormData({ ...formData, minimum_sample_size: parseInt(e.target.value) || 5 })}
                    className="w-full bg-[#161B26] border border-[#1F2937] rounded-lg p-2.5 text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              {/* Source Content Association */}
              <div className="bg-[#161B26]/30 border border-[#1F2937] p-3 rounded-lg space-y-3">
                <div className="font-semibold text-indigo-400 flex items-center gap-1 text-[11px]">
                  <FileText className="w-3.5 h-3.5" />
                  Content Association (Single Variable Check)
                </div>

                <div className="space-y-2">
                  <div className="space-y-1">
                    <label className="block text-gray-500 text-[10px]">Control Source Content *</label>
                    <select
                      required
                      value={formData.control_content_id}
                      onChange={(e) => setFormData({ ...formData, control_content_id: e.target.value })}
                      className="w-full bg-[#161B26] border border-[#1F2937] rounded-lg p-2 text-white focus:outline-none"
                    >
                      <option value="">-- Select Content --</option>
                      {contents.map(c => (
                        <option key={c.id} value={c.id}>{c.title || c.id}</option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="block text-gray-500 text-[10px]">Treatment Source Content * (Usually same as control)</label>
                    <select
                      required
                      value={formData.treatment_content_id}
                      onChange={(e) => setFormData({ ...formData, treatment_content_id: e.target.value })}
                      className="w-full bg-[#161B26] border border-[#1F2937] rounded-lg p-2 text-white focus:outline-none"
                    >
                      <option value="">-- Select Content --</option>
                      {contents.map(c => (
                        <option key={c.id} value={c.id}>{c.title || c.id}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#1F2937]">
                <button
                  type="button"
                  onClick={() => setShowWizard(false)}
                  className="px-4 py-2 font-semibold text-gray-400 hover:text-white bg-transparent border border-transparent transition-colors"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={creating}
                  className="flex items-center gap-1 px-4 py-2 font-semibold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg transition-colors"
                >
                  {creating && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  Create Experiment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
