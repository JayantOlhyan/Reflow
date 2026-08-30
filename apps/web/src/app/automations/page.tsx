"use client";

import React, { useState, useEffect } from 'react';
import { 
  AutomationRule, AutomationExecution, AutomationActionExecution, AutomationDetailResponse
} from '@/types';
import { api } from '@/lib/api';
import { 
  Cpu, Play, Pause, Plus, RefreshCw, AlertTriangle, CheckCircle, XCircle, Trash2, 
  Eye, Zap, Shield, HelpCircle, FileText, ChevronRight, Check, AlertCircle, Clock
} from 'lucide-react';

export default function AutomationsPage() {
  const [rules, setRules] = useState<AutomationRule[]>([]);
  const [selectedRule, setSelectedRule] = useState<AutomationDetailResponse | null>(null);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [creating, setCreating] = useState(false);
  const [running, setRunning] = useState<string | null>(null);
  const [dryRunning, setDryRunning] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Content for dry-runs & testing
  const [contents, setContents] = useState<any[]>([]);
  const [selectedContentId, setSelectedContentId] = useState('');
  const [dryRunResult, setDryRunResult] = useState<any>(null);

  // Wizard state
  const [showWizard, setShowWizard] = useState(false);
  const [wizardStep, setWizardStep] = useState(1);
  
  // Wizard creation form fields
  const [wizardData, setWizardData] = useState({
    name: '',
    description: '',
    trigger_type: 'CONTENT_READY',
    scope: 'AUTO_APPROVE',
    conditions: [] as any[],
    actions: [] as any[],
    cooldown_minutes: 60,
    max_runs_per_day: 5
  });

  // Current building condition
  const [newCondition, setNewCondition] = useState({
    field: 'content_type',
    operator: '==',
    value: 'VIDEO'
  });

  // Current building action
  const [newAction, setNewAction] = useState({
    type: 'GENERATE_CLIPS',
    platform: 'linkedin',
    platforms: ['LINKEDIN', 'X'] as string[],
    target_count: 3,
    burn_captions: false,
    caption_style: 'BOLD_PUNCH'
  });

  const loadRules = async () => {
    try {
      setLoadingList(true);
      const list = await api.getAutomationRules();
      setRules(list || []);
    } catch (err: any) {
      console.error("Failed to load rules:", err);
      setErrorMsg("Failed to load automation rules.");
    } finally {
      setLoadingList(false);
    }
  };

  const loadContents = async () => {
    try {
      const res = await api.getContentList();
      setContents(res.items || []);
      if (res.items && res.items.length > 0) {
        setSelectedContentId(res.items[0].id);
      }
    } catch (err) {
      console.error("Failed to load contents:", err);
    }
  };

  useEffect(() => {
    loadRules();
    loadContents();
  }, []);

  const handleSelectRule = async (id: string) => {
    try {
      setLoadingDetails(true);
      setErrorMsg(null);
      setDryRunResult(null);
      const details = await api.getAutomationRule(id);
      setSelectedRule(details);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load automation details.");
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleToggleEnable = async (rule: AutomationRule) => {
    try {
      setErrorMsg(null);
      if (rule.enabled) {
        await api.disableAutomationRule(rule.id);
      } else {
        await api.enableAutomationRule(rule.id);
      }
      await loadRules();
      if (selectedRule && selectedRule.rule.id === rule.id) {
        await handleSelectRule(rule.id);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to toggle rule state.");
    }
  };

  const handleDeleteRule = async (id: string) => {
    if (!confirm("Are you sure you want to delete this rule?")) return;
    try {
      setErrorMsg(null);
      await api.deleteAutomationRule(id);
      setSelectedRule(null);
      await loadRules();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to delete rule.");
    }
  };

  const handleManualRun = async (id: string) => {
    if (!selectedContentId) {
      setErrorMsg("Please select a content item to trigger the run.");
      return;
    }
    try {
      setRunning(id);
      setErrorMsg(null);
      await api.runAutomationRuleManual(id, selectedContentId);
      setSuccessMsg("Manual execution queued successfully.");
      await handleSelectRule(id);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to trigger manual execution.");
    } finally {
      setRunning(null);
    }
  };

  const handleDryRun = async (id: string) => {
    if (!selectedContentId) {
      setErrorMsg("Please select a content item to test dry-run.");
      return;
    }
    try {
      setDryRunning(id);
      setErrorMsg(null);
      setDryRunResult(null);
      const res = await api.dryRunAutomationRule(id, selectedContentId);
      setDryRunResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Dry run failed.");
    } finally {
      setDryRunning(null);
    }
  };

  const handleCreateFromTemplate = async (templateName: string) => {
    try {
      setErrorMsg(null);
      const customName = prompt("Enter a name for this automation:", `My ${templateName.replace(/_/g, ' ')}`);
      if (!customName) return;

      await api.createAutomationRuleFromTemplate(templateName, customName);
      setSuccessMsg("Automation created from template!");
      await loadRules();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to instantiate template.");
    }
  };

  const handleSaveWizard = async () => {
    if (!wizardData.name.trim()) {
      setErrorMsg("Automation name is required.");
      return;
    }
    try {
      setErrorMsg(null);
      const newRule = await api.createAutomationRule(wizardData);
      setSuccessMsg(`Automation '${newRule.name}' created successfully!`);
      setShowWizard(false);
      // Reset form
      setWizardData({
        name: '',
        description: '',
        trigger_type: 'CONTENT_READY',
        scope: 'AUTO_APPROVE',
        conditions: [],
        actions: [],
        cooldown_minutes: 60,
        max_runs_per_day: 5
      });
      setWizardStep(1);
      await loadRules();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to save rule.");
    }
  };

  const addCondition = () => {
    setWizardData({
      ...wizardData,
      conditions: [...wizardData.conditions, { ...newCondition }]
    });
  };

  const removeCondition = (idx: number) => {
    const updated = [...wizardData.conditions];
    updated.splice(idx, 1);
    setWizardData({ ...wizardData, conditions: updated });
  };

  const addAction = () => {
    setWizardData({
      ...wizardData,
      actions: [...wizardData.actions, { ...newAction }]
    });
  };

  const removeAction = (idx: number) => {
    const updated = [...wizardData.actions];
    updated.splice(idx, 1);
    setWizardData({ ...wizardData, actions: updated });
  };

  const activeRules = rules.filter(r => r.enabled);
  const pausedRules = rules.filter(r => !r.enabled);

  return (
    <div className="min-h-screen bg-[#0B0D12] text-[#F3F4F6] p-6 lg:p-12">
      {/* Title */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight flex items-center gap-3 text-white">
            <Cpu className="w-8 h-8 text-indigo-500" />
            Automation & Distribution Engine
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Configure closed-loop workflows to automatically transform, schedule, and publish your content.
          </p>
        </div>

        <button 
          onClick={() => { setShowWizard(true); setErrorMsg(null); }}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg text-sm transition-all"
        >
          <Plus className="w-4 h-4" />
          Create Automation
        </button>
      </div>

      {/* Messages */}
      {errorMsg && (
        <div className="mb-6 p-4 bg-red-950/40 border border-red-800 text-red-300 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <div>{errorMsg}</div>
        </div>
      )}
      {successMsg && (
        <div className="mb-6 p-4 bg-green-950/40 border border-green-800 text-green-300 rounded-lg flex items-start gap-3">
          <CheckCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <div>{successMsg}</div>
        </div>
      )}

      {/* Quick Templates */}
      <div className="mb-10">
        <h3 className="text-md font-semibold text-gray-300 mb-4">Pre-packaged Templates</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-[#111827] border border-[#1F2937] p-5 rounded-xl hover:border-indigo-500/50 transition-all flex flex-col justify-between">
            <div>
              <div className="font-bold text-white mb-1">Long Video → Shorts</div>
              <p className="text-xs text-gray-400">Discover vertical clips, render them, and burn BOLD_PUNCH captions automatically whenever video content is uploaded.</p>
            </div>
            <button 
              onClick={() => handleCreateFromTemplate('auto_clip_generator')}
              className="mt-4 text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
            >
              Use Template <ChevronRight className="w-3 h-3" />
            </button>
          </div>

          <div className="bg-[#111827] border border-[#1F2937] p-5 rounded-xl hover:border-indigo-500/50 transition-all flex flex-col justify-between">
            <div>
              <div className="font-bold text-white mb-1">Auto Carousel Generator</div>
              <p className="text-xs text-gray-400">Plan and rasterize full slide deck carousels in EDITORIAL template when text content is marked READY.</p>
            </div>
            <button 
              onClick={() => handleCreateFromTemplate('auto_carousel_generator')}
              className="mt-4 text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
            >
              Use Template <ChevronRight className="w-3 h-3" />
            </button>
          </div>

          <div className="bg-[#111827] border border-[#1F2937] p-5 rounded-xl hover:border-indigo-500/50 transition-all flex flex-col justify-between">
            <div>
              <div className="font-bold text-white mb-1">Auto Social Distribution</div>
              <p className="text-xs text-gray-400">Instantly generate cross-platform captions and queue scheduling when you approve a video variant.</p>
            </div>
            <button 
              onClick={() => handleCreateFromTemplate('auto_social_distribution')}
              className="mt-4 text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
            >
              Use Template <ChevronRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Rules List */}
        <div className="lg:col-span-1 space-y-6">
          {/* Active Rules */}
          <div>
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Active Rules ({activeRules.length})</h3>
            {activeRules.length === 0 ? (
              <div className="p-4 bg-[#111827]/40 text-center text-xs text-gray-500 rounded-lg border border-dashed border-[#1F2937]">
                No active automations.
              </div>
            ) : (
              <div className="space-y-3">
                {activeRules.map(rule => (
                  <div 
                    key={rule.id}
                    onClick={() => handleSelectRule(rule.id)}
                    className={`p-4 bg-[#111827] border rounded-lg cursor-pointer transition-all flex items-center justify-between ${
                      selectedRule?.rule.id === rule.id ? 'border-indigo-500' : 'border-[#1F2937] hover:border-gray-700'
                    }`}
                  >
                    <div className="truncate pr-2">
                      <div className="font-medium text-white truncate text-sm">{rule.name}</div>
                      <div className="text-[10px] text-indigo-400 uppercase font-semibold mt-0.5">{rule.trigger_type}</div>
                    </div>
                    <button 
                      onClick={(e) => { e.stopPropagation(); handleToggleEnable(rule); }}
                      className="px-2 py-1 bg-green-950/40 border border-green-800 text-green-300 text-[10px] font-semibold rounded hover:bg-green-900/40 transition-all flex items-center gap-1"
                    >
                      <Play className="w-2.5 h-2.5 fill-current" /> Active
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Paused/Disabled Rules */}
          <div>
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Paused / Error Rules ({pausedRules.length})</h3>
            {pausedRules.length === 0 ? (
              <div className="p-4 bg-[#111827]/40 text-center text-xs text-gray-500 rounded-lg border border-dashed border-[#1F2937]">
                No paused rules.
              </div>
            ) : (
              <div className="space-y-3">
                {pausedRules.map(rule => (
                  <div 
                    key={rule.id}
                    onClick={() => handleSelectRule(rule.id)}
                    className={`p-4 bg-[#111827] border rounded-lg cursor-pointer transition-all flex items-center justify-between ${
                      selectedRule?.rule.id === rule.id ? 'border-red-500' : 'border-[#1F2937] hover:border-gray-700'
                    }`}
                  >
                    <div className="truncate pr-2">
                      <div className="font-medium text-white truncate text-sm">{rule.name}</div>
                      <div className="text-[10px] text-gray-500 mt-0.5">{rule.status === 'ERROR' ? 'PAUSED ON ERROR' : 'PAUSED'}</div>
                    </div>
                    <button 
                      onClick={(e) => { e.stopPropagation(); handleToggleEnable(rule); }}
                      className="px-2 py-1 bg-[#1F2937] border border-gray-700 text-gray-300 text-[10px] font-semibold rounded hover:bg-gray-800 transition-all flex items-center gap-1"
                    >
                      <Pause className="w-2.5 h-2.5 fill-current" /> Paused
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Selected Rule Details */}
        <div className="lg:col-span-2">
          {loadingDetails ? (
            <div className="bg-[#111827] border border-[#1F2937] p-12 rounded-xl flex flex-col items-center justify-center text-gray-400 gap-3">
              <RefreshCw className="w-8 h-8 animate-spin text-indigo-500" />
              <span>Fetching automation details...</span>
            </div>
          ) : selectedRule ? (
            <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-6 lg:p-8 space-y-6">
              
              {/* Header */}
              <div className="flex justify-between items-start border-b border-[#1F2937] pb-5">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-bold text-white">{selectedRule.rule.name}</h2>
                    {selectedRule.rule.status === 'ERROR' && (
                      <span className="px-2 py-0.5 bg-red-950/40 border border-red-800 text-red-300 text-[10px] font-semibold rounded-full flex items-center gap-1">
                        <AlertTriangle className="w-2.5 h-2.5" /> ERROR
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-400 mt-1">{selectedRule.rule.description || 'No description provided.'}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button 
                    onClick={() => handleToggleEnable(selectedRule.rule)}
                    className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300 text-xs font-semibold flex items-center gap-1 transition-all"
                  >
                    {selectedRule.rule.enabled ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                    {selectedRule.rule.enabled ? 'Pause' : 'Activate'}
                  </button>
                  <button 
                    onClick={() => handleDeleteRule(selectedRule.rule.id)}
                    className="p-2 bg-red-950/20 hover:bg-red-950/60 border border-red-900/30 text-red-400 hover:text-red-300 rounded-lg transition-all"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Stats Card */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-[#0B0D12] p-4 rounded-xl border border-[#1F2937]">
                <div>
                  <div className="text-xs text-gray-400">Total Runs</div>
                  <div className="text-lg font-bold text-white mt-0.5">{selectedRule.metrics.total_runs}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-400">Success Rate</div>
                  <div className="text-lg font-bold text-green-400 mt-0.5">{selectedRule.metrics.success_rate.toFixed(1)}%</div>
                </div>
                <div>
                  <div className="text-xs text-gray-400">Skipped Runs</div>
                  <div className="text-lg font-bold text-yellow-400 mt-0.5">{selectedRule.metrics.skipped_runs}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-400">Failed Runs</div>
                  <div className="text-lg font-bold text-red-400 mt-0.5">{selectedRule.metrics.failed_runs}</div>
                </div>
              </div>

              {/* Pipeline Logic Flow Visualizer */}
              <div>
                <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-1.5">
                  <Zap className="w-4 h-4 text-indigo-400" /> Pipeline Configuration
                </h3>
                <div className="bg-[#0B0D12] border border-[#1F2937] p-5 rounded-xl space-y-4">
                  <div>
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider">WHEN EVENT OCCURS:</span>
                    <div className="text-sm font-semibold text-white mt-1 uppercase text-indigo-400">{selectedRule.rule.trigger_type}</div>
                  </div>

                  {selectedRule.rule.conditions.length > 0 && (
                    <div>
                      <span className="text-[10px] text-gray-500 uppercase tracking-wider">IF CONDITIONS MATCH:</span>
                      <div className="space-y-1.5 mt-1.5">
                        {selectedRule.rule.conditions.map((cond, idx) => (
                          <div key={idx} className="text-xs flex items-center gap-2 bg-[#111827] px-3 py-1.5 rounded border border-[#1F2937] w-fit">
                            <span className="text-gray-400">{cond.field}</span>
                            <span className="text-indigo-400 font-mono font-bold">{cond.operator}</span>
                            <span className="text-white font-semibold">{cond.value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div>
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider">THEN EXECUTE ACTIONS:</span>
                    <div className="space-y-2 mt-2">
                      {selectedRule.rule.actions.map((act, idx) => (
                        <div key={idx} className="text-xs bg-[#111827] border border-[#1F2937] p-3 rounded-lg flex items-center justify-between">
                          <div>
                            <span className="font-bold text-white block">{act.type}</span>
                            <span className="text-[10px] text-gray-400">
                              {act.type === 'GENERATE_CLIPS' && `Target clips: ${act.target_count || 3} styled as ${act.caption_style}`}
                              {act.type === 'GENERATE_CAROUSEL' && `Template: ${act.template || 'MINIMAL'} count: ${act.slide_count || 5}`}
                              {act.type === 'PUBLISH' && `Platform: ${act.platform}`}
                              {act.type === 'SCHEDULE_PUBLICATION' && `Platform: ${act.platform} delay: ${act.delay_hours || 2}h`}
                              {act.type === 'CREATE_EXPERIMENT' && `Metric: ${act.primary_metric || 'engagement_rate'} scope: ${act.scope || 'HOOK'}`}
                              {act.type === 'SEND_NOTIFICATION' && `Custom notification alert`}
                            </span>
                          </div>
                          <span className="px-2 py-0.5 bg-[#1F2937] text-[9px] font-semibold text-gray-300 rounded uppercase">
                            {selectedRule.rule.scope === 'REQUIRE_APPROVAL' ? 'Requires Approval' : 'Auto Approve'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Limits and safety constraints */}
              <div className="border-t border-[#1F2937] pt-5">
                <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-1.5">
                  <Shield className="w-4 h-4 text-green-400" /> Safety & Guardrails
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="bg-[#0B0D12] p-3 rounded-lg border border-[#1F2937] flex justify-between items-center">
                    <span className="text-gray-400">Cooldown limit:</span>
                    <span className="font-semibold text-white">{selectedRule.rule.cooldown_minutes} minutes</span>
                  </div>
                  <div className="bg-[#0B0D12] p-3 rounded-lg border border-[#1F2937] flex justify-between items-center">
                    <span className="text-gray-400">Max runs/day:</span>
                    <span className="font-semibold text-white">{selectedRule.rule.max_runs_per_day} runs</span>
                  </div>
                  <div className="bg-[#0B0D12] p-3 rounded-lg border border-[#1F2937] flex justify-between items-center">
                    <span className="text-gray-400">Last run timestamp:</span>
                    <span className="font-semibold text-white">
                      {selectedRule.rule.last_run_at ? new Date(selectedRule.rule.last_run_at).toLocaleString() : 'Never'}
                    </span>
                  </div>
                  <div className="bg-[#0B0D12] p-3 rounded-lg border border-[#1F2937] flex justify-between items-center">
                    <span className="text-gray-400">Next eligible run:</span>
                    <span className="font-semibold text-white">
                      {selectedRule.rule.next_run_at ? new Date(selectedRule.rule.next_run_at).toLocaleString() : 'Immediate'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Execution testing / dry run */}
              <div className="border-t border-[#1F2937] pt-5 space-y-4">
                <h3 className="text-sm font-semibold text-gray-300">Run Preview & Testing</h3>
                <div className="flex flex-col md:flex-row gap-4 items-end bg-[#0B0D12] p-4 rounded-xl border border-[#1F2937]">
                  <div className="w-full md:w-2/3 space-y-1.5">
                    <label className="text-[10px] text-gray-400 uppercase tracking-wider block">Select Content to Test</label>
                    <select 
                      value={selectedContentId}
                      onChange={(e) => setSelectedContentId(e.target.value)}
                      className="w-full bg-[#111827] border border-[#1F2937] text-sm text-white p-2.5 rounded-lg focus:outline-none focus:border-indigo-500"
                    >
                      {contents.map(c => (
                        <option key={c.id} value={c.id}>[{c.content_type}] {c.title}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex gap-2 w-full md:w-auto shrink-0">
                    <button 
                      onClick={() => handleDryRun(selectedRule.rule.id)}
                      disabled={dryRunning === selectedRule.rule.id}
                      className="flex-1 md:flex-initial px-4 py-2.5 bg-[#1F2937] hover:bg-gray-800 text-gray-300 font-semibold text-xs rounded-lg transition-all flex items-center justify-center gap-1.5"
                    >
                      {dryRunning === selectedRule.rule.id ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Eye className="w-3.5 h-3.5" />}
                      Dry Run
                    </button>
                    <button 
                      onClick={() => handleManualRun(selectedRule.rule.id)}
                      disabled={running === selectedRule.rule.id}
                      className="flex-1 md:flex-initial px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg transition-all flex items-center justify-center gap-1.5"
                    >
                      {running === selectedRule.rule.id ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                      Run Now
                    </button>
                  </div>
                </div>

                {dryRunResult && (
                  <div className="bg-[#111827] border border-[#1F2937] p-4 rounded-lg space-y-2">
                    <div className="font-bold text-xs flex items-center gap-2">
                      {dryRunResult.conditions_passed ? (
                        <span className="text-green-400 flex items-center gap-1"><Check className="w-4 h-4" /> Conditions Passed</span>
                      ) : (
                        <span className="text-yellow-400 flex items-center gap-1"><AlertTriangle className="w-4 h-4" /> Conditions Failed</span>
                      )}
                    </div>
                    <div className="text-xs text-gray-400">{dryRunResult.preview_message}</div>
                  </div>
                )}
              </div>

              {/* Execution History */}
              <div className="border-t border-[#1F2937] pt-5">
                <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-1.5">
                  <Clock className="w-4 h-4 text-indigo-400" /> Recent Runs & Executions
                </h3>
                {selectedRule.executions.length === 0 ? (
                  <div className="p-6 text-center text-xs text-gray-500 bg-[#0B0D12] rounded-lg border border-[#1F2937]">
                    No executions recorded.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs text-gray-400">
                      <thead className="bg-[#0B0D12] text-gray-300 border-b border-[#1F2937]">
                        <tr>
                          <th className="p-3">Run ID</th>
                          <th className="p-3">Trigger Event</th>
                          <th className="p-3">Entity</th>
                          <th className="p-3">Status</th>
                          <th className="p-3">Timestamp</th>
                          <th className="p-3">Error/Reason</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#1F2937]">
                        {selectedRule.executions.map(exec => (
                          <tr key={exec.id} className="hover:bg-[#0B0D12]">
                            <td className="p-3 font-mono text-[10px] text-gray-300">{exec.id}</td>
                            <td className="p-3 capitalize">{exec.trigger_event}</td>
                            <td className="p-3 font-mono text-[10px]">{exec.trigger_entity_id}</td>
                            <td className="p-3">
                              <span className={`px-2 py-0.5 text-[9px] font-bold rounded-full uppercase ${
                                exec.status === 'SUCCEEDED' ? 'bg-green-950/40 text-green-400 border border-green-900/30' :
                                exec.status === 'FAILED' ? 'bg-red-950/40 text-red-400 border border-red-900/30' :
                                exec.status === 'SKIPPED' ? 'bg-yellow-950/40 text-yellow-400 border border-yellow-900/30' :
                                exec.status === 'WAITING' ? 'bg-indigo-950/40 text-indigo-400 border border-indigo-900/30' :
                                'bg-[#1F2937] text-gray-300'
                              }`}>
                                {exec.status}
                              </span>
                            </td>
                            <td className="p-3">{new Date(exec.created_at).toLocaleString()}</td>
                            <td className="p-3 text-[10px] text-gray-500 truncate max-w-[150px]">{exec.error || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

            </div>
          ) : (
            <div className="bg-[#111827] border border-[#1F2937] p-24 rounded-xl flex flex-col items-center justify-center text-gray-500 gap-4 text-center">
              <Cpu className="w-16 h-16 text-gray-700" />
              <div>
                <div className="text-md font-bold text-white">No Automation Selected</div>
                <p className="text-xs text-gray-500 mt-1 max-w-[280px]">Select an automation rule from the left panel to preview details, dry-run, or view executions logs.</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Creation Wizard Modal */}
      {showWizard && (
        <div className="fixed inset-0 z-50 bg-[#000]/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-[#1F2937] w-full max-w-xl rounded-xl p-6 lg:p-8 space-y-6 shadow-2xl relative">
            
            {/* Steps Indicator */}
            <div className="flex items-center justify-between border-b border-[#1F2937] pb-4">
              <h3 className="text-md font-extrabold text-white">Create Automation Rule</h3>
              <span className="text-xs font-semibold text-indigo-400">Step {wizardStep} of 6</span>
            </div>

            {wizardStep === 1 && (
              <div className="space-y-4">
                <div className="font-bold text-sm text-gray-200">Step 1: Choose trigger</div>
                <div className="space-y-1">
                  <label className="text-[10px] text-gray-400 uppercase tracking-wider block">Automation Name</label>
                  <input 
                    type="text"
                    value={wizardData.name}
                    onChange={(e) => setWizardData({ ...wizardData, name: e.target.value })}
                    placeholder="E.g. Auto Clip Publisher"
                    className="w-full bg-[#0B0D12] border border-[#1F2937] text-sm text-white p-2.5 rounded-lg focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] text-gray-400 uppercase tracking-wider block">Description</label>
                  <textarea 
                    value={wizardData.description}
                    onChange={(e) => setWizardData({ ...wizardData, description: e.target.value })}
                    placeholder="Enter what this automation accomplishes"
                    rows={2}
                    className="w-full bg-[#0B0D12] border border-[#1F2937] text-sm text-white p-2.5 rounded-lg focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] text-gray-400 uppercase tracking-wider block">Trigger Event Type</label>
                  <select 
                    value={wizardData.trigger_type}
                    onChange={(e) => setWizardData({ ...wizardData, trigger_type: e.target.value })}
                    className="w-full bg-[#0B0D12] border border-[#1F2937] text-sm text-white p-2.5 rounded-lg focus:outline-none focus:border-indigo-500"
                  >
                    <option value="CONTENT_READY">CONTENT_READY (Video/Text draft uploaded)</option>
                    <option value="CLIP_CREATED">CLIP_CREATED (AI clip variant is ready)</option>
                    <option value="CAROUSEL_READY">CAROUSEL_READY (Slide deck is rendered)</option>
                    <option value="CONTENT_APPROVED">CONTENT_APPROVED (Human approves content)</option>
                    <option value="ANALYTICS_UPDATED">ANALYTICS_UPDATED (Telemetry sync checks completed)</option>
                    <option value="EXPERIMENT_COMPLETED">EXPERIMENT_COMPLETED (A/B evaluation finishes)</option>
                    <option value="RECOMMENDATION_CREATED">RECOMMENDATION_CREATED (AI pattern recommendation)</option>
                  </select>
                </div>
              </div>
            )}

            {wizardStep === 2 && (
              <div className="space-y-4">
                <div className="font-bold text-sm text-gray-200">Step 2: Choose conditions (Optional)</div>
                <div className="bg-[#0B0D12] p-4 border border-[#1F2937] rounded-lg grid grid-cols-3 gap-2">
                  <div>
                    <select 
                      value={newCondition.field}
                      onChange={(e) => setNewCondition({ ...newCondition, field: e.target.value })}
                      className="w-full bg-[#111827] border border-[#1F2937] text-xs text-white p-2 rounded"
                    >
                      <option value="content_type">content_type</option>
                      <option value="duration">duration (seconds)</option>
                      <option value="status">status</option>
                    </select>
                  </div>
                  <div>
                    <select 
                      value={newCondition.operator}
                      onChange={(e) => setNewCondition({ ...newCondition, operator: e.target.value })}
                      className="w-full bg-[#111827] border border-[#1F2937] text-xs text-white p-2 rounded"
                    >
                      <option value="==">equals (==)</option>
                      <option value="!=">not equals (!=)</option>
                      <option value=">">greater than (&gt;)</option>
                      <option value="<">less than (&lt;)</option>
                    </select>
                  </div>
                  <div className="flex gap-2">
                    <input 
                      type="text"
                      value={newCondition.value}
                      onChange={(e) => setNewCondition({ ...newCondition, value: e.target.value })}
                      className="w-full bg-[#111827] border border-[#1F2937] text-xs text-white p-2 rounded"
                    />
                    <button 
                      onClick={addCondition}
                      className="px-3 bg-indigo-600 hover:bg-indigo-700 text-xs font-semibold rounded text-white"
                    >
                      Add
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-[10px] text-gray-400 uppercase tracking-wider">Active Conditions Checklist:</div>
                  {wizardData.conditions.length === 0 ? (
                    <div className="text-xs text-gray-500 italic">No conditions added. Runs unconditionally on trigger.</div>
                  ) : (
                    <div className="space-y-2">
                      {wizardData.conditions.map((c, idx) => (
                        <div key={idx} className="flex justify-between items-center text-xs bg-[#0B0D12] p-2 rounded border border-[#1F2937]">
                          <span>{c.field} {c.operator} {c.value}</span>
                          <button onClick={() => removeCondition(idx)} className="text-red-400 hover:text-red-300">Remove</button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {wizardStep === 3 && (
              <div className="space-y-4">
                <div className="font-bold text-sm text-gray-200">Step 3: Choose actions</div>
                <div className="bg-[#0B0D12] p-4 border border-[#1F2937] rounded-lg space-y-3">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[9px] text-gray-400 uppercase">Action Type</label>
                      <select 
                        value={newAction.type}
                        onChange={(e) => setNewAction({ ...newAction, type: e.target.value })}
                        className="w-full bg-[#111827] border border-[#1F2937] text-xs text-white p-2 rounded"
                      >
                        <option value="GENERATE_CLIPS">GENERATE_CLIPS</option>
                        <option value="GENERATE_CAROUSEL">GENERATE_CAROUSEL</option>
                        <option value="GENERATE_PLATFORM_COPY">GENERATE_PLATFORM_COPY</option>
                        <option value="SCHEDULE_PUBLICATION">SCHEDULE_PUBLICATION</option>
                        <option value="PUBLISH">PUBLISH</option>
                        <option value="CREATE_EXPERIMENT">CREATE_EXPERIMENT</option>
                        <option value="SEND_NOTIFICATION">SEND_NOTIFICATION</option>
                      </select>
                    </div>

                    {newAction.type === 'SCHEDULE_PUBLICATION' || newAction.type === 'PUBLISH' ? (
                      <div>
                        <label className="text-[9px] text-gray-400 uppercase">Platform Destination</label>
                        <select 
                          value={newAction.platform}
                          onChange={(e) => setNewAction({ ...newAction, platform: e.target.value })}
                          className="w-full bg-[#111827] border border-[#1F2937] text-xs text-white p-2 rounded"
                        >
                          <option value="linkedin">LinkedIn</option>
                          <option value="x">X (Twitter)</option>
                          <option value="youtube">YouTube</option>
                          <option value="instagram">Instagram</option>
                        </select>
                      </div>
                    ) : newAction.type === 'GENERATE_CLIPS' ? (
                      <div>
                        <label className="text-[9px] text-gray-400 uppercase">Caption style</label>
                        <select 
                          value={newAction.caption_style}
                          onChange={(e) => setNewAction({ ...newAction, caption_style: e.target.value })}
                          className="w-full bg-[#111827] border border-[#1F2937] text-xs text-white p-2 rounded"
                        >
                          <option value="BOLD_PUNCH">BOLD_PUNCH</option>
                          <option value="CLEAN_SUBTITLE">CLEAN_SUBTITLE</option>
                          <option value="KINETIC_HIGHLIGHT">KINETIC_HIGHLIGHT</option>
                        </select>
                      </div>
                    ) : (
                      <div className="opacity-40">
                        <label className="text-[9px] text-gray-400 uppercase">Additional params</label>
                        <input type="text" disabled placeholder="N/A" className="w-full bg-[#111827] border border-[#1F2937] text-xs text-white p-2 rounded" />
                      </div>
                    )}
                  </div>
                  <button 
                    onClick={addAction}
                    className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-xs font-semibold rounded text-white"
                  >
                    Add Action to Flow
                  </button>
                </div>

                <div className="space-y-2">
                  <div className="text-[10px] text-gray-400 uppercase tracking-wider">Configured Actions Flow:</div>
                  {wizardData.actions.length === 0 ? (
                    <div className="text-xs text-gray-500 italic">Please add at least one action to proceed.</div>
                  ) : (
                    <div className="space-y-2">
                      {wizardData.actions.map((a, idx) => (
                        <div key={idx} className="flex justify-between items-center text-xs bg-[#0B0D12] p-2 rounded border border-[#1F2937]">
                          <span className="font-semibold text-white">{a.type}</span>
                          <button onClick={() => removeAction(idx)} className="text-red-400 hover:text-red-300">Remove</button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {wizardStep === 4 && (
              <div className="space-y-4">
                <div className="font-bold text-sm text-gray-200">Step 4: Configure approval gates</div>
                <div className="space-y-3">
                  <label className="text-[10px] text-gray-400 uppercase tracking-wider block">Approval Mode</label>
                  <div className="grid grid-cols-2 gap-4">
                    <div 
                      onClick={() => setWizardData({ ...wizardData, scope: 'AUTO_APPROVE' })}
                      className={`p-4 border rounded-lg cursor-pointer text-center ${
                        wizardData.scope === 'AUTO_APPROVE' ? 'border-indigo-500 bg-indigo-950/20' : 'border-[#1F2937] hover:border-gray-800'
                      }`}
                    >
                      <div className="font-bold text-xs text-white">Auto Approve</div>
                      <div className="text-[10px] text-gray-400 mt-1">Actions publish automatically without human intervention.</div>
                    </div>
                    <div 
                      onClick={() => setWizardData({ ...wizardData, scope: 'REQUIRE_APPROVAL' })}
                      className={`p-4 border rounded-lg cursor-pointer text-center ${
                        wizardData.scope === 'REQUIRE_APPROVAL' ? 'border-indigo-500 bg-indigo-950/20' : 'border-[#1F2937] hover:border-gray-800'
                      }`}
                    >
                      <div className="font-bold text-xs text-white">Require Approval</div>
                      <div className="text-[10px] text-gray-400 mt-1">All generated copies/publications must be manually approved.</div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {wizardStep === 5 && (
              <div className="space-y-4">
                <div className="font-bold text-sm text-gray-200">Step 5: Configure safety limits</div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] text-gray-400 uppercase block">Cooldown Time (Minutes)</label>
                    <input 
                      type="number"
                      value={wizardData.cooldown_minutes}
                      onChange={(e) => setWizardData({ ...wizardData, cooldown_minutes: parseInt(e.target.value) })}
                      className="w-full bg-[#0B0D12] border border-[#1F2937] text-sm text-white p-2.5 rounded-lg"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] text-gray-400 uppercase block">Max Runs per Day</label>
                    <input 
                      type="number"
                      value={wizardData.max_runs_per_day}
                      onChange={(e) => setWizardData({ ...wizardData, max_runs_per_day: parseInt(e.target.value) })}
                      className="w-full bg-[#0B0D12] border border-[#1F2937] text-sm text-white p-2.5 rounded-lg"
                    />
                  </div>
                </div>
                <p className="text-[10px] text-gray-400 mt-2">These parameters protect the platform from runaway API calls or duplicate scheduling loops.</p>
              </div>
            )}

            {wizardStep === 6 && (
              <div className="space-y-4">
                <div className="font-bold text-sm text-gray-200">Step 6: Review & Enable</div>
                <div className="bg-[#0B0D12] p-4 border border-[#1F2937] rounded-xl text-xs space-y-3">
                  <div>
                    <span className="text-gray-400 block font-semibold">Name:</span>
                    <span className="text-white text-sm font-bold">{wizardData.name}</span>
                  </div>
                  <div>
                    <span className="text-gray-400 block font-semibold">Trigger:</span>
                    <span className="text-white font-mono text-indigo-400 uppercase">{wizardData.trigger_type}</span>
                  </div>
                  <div>
                    <span className="text-gray-400 block font-semibold">Behavior preview statement:</span>
                    <span className="text-white font-medium italic block mt-1">
                      "This automation will execute {wizardData.actions.length} action(s) with {
                        wizardData.scope === 'REQUIRE_APPROVAL' ? 'REQUIRED HUMAN APPROVAL' : 'AUTOMATIC PUBLISHING'
                      } whenever {wizardData.trigger_type} occurs, capped at {wizardData.max_runs_per_day} times/day."
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Modal Controls */}
            <div className="flex justify-between items-center border-t border-[#1F2937] pt-4">
              <button 
                onClick={() => setShowWizard(false)}
                className="px-4 py-2 text-xs font-semibold text-gray-400 hover:text-gray-200"
              >
                Cancel
              </button>
              <div className="flex gap-2">
                {wizardStep > 1 && (
                  <button 
                    onClick={() => setWizardStep(wizardStep - 1)}
                    className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-semibold rounded-lg"
                  >
                    Back
                  </button>
                )}
                {wizardStep < 6 ? (
                  <button 
                    onClick={() => setWizardStep(wizardStep + 1)}
                    disabled={wizardStep === 3 && wizardData.actions.length === 0}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white text-xs font-semibold rounded-lg"
                  >
                    Next
                  </button>
                ) : (
                  <button 
                    onClick={handleSaveWizard}
                    className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-xs font-semibold rounded-lg"
                  >
                    Enable Automation
                  </button>
                )}
              </div>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
