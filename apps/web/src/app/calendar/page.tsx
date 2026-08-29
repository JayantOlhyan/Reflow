"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { 
  Calendar as CalendarIcon, 
  ChevronLeft, 
  ChevronRight, 
  Plus, 
  Clock, 
  Share2, 
  AlertCircle, 
  CheckCircle2, 
  RefreshCw, 
  ExternalLink, 
  X, 
  Film, 
  Trash2, 
  CalendarDays, 
  SlidersHorizontal,
  Lock,
  RotateCcw
} from 'lucide-react';
import { 
  CalendarEventItem, 
  ContentItem, 
  PlatformConnectionItem, 
  PublicationItem 
} from '@/types';
import { api } from '@/lib/api';
import { 
  YoutubeIcon, 
  InstagramIcon, 
  TiktokIcon, 
  LinkedinIcon, 
  XIcon, 
  FacebookIcon 
} from '@/components/ui/SocialIcons';

const COMMON_TIMEZONES = [
  { value: 'UTC', label: 'UTC (Coordinated Universal Time)' },
  { value: 'Asia/Kolkata', label: 'Asia/Kolkata (IST, UTC+5:30)' },
  { value: 'America/New_York', label: 'America/New_York (EST/EDT, UTC-5/-4)' },
  { value: 'America/Los_Angeles', label: 'America/Los_Angeles (PST/PDT, UTC-8/-7)' },
  { value: 'America/Chicago', label: 'America/Chicago (CST/CDT, UTC-6/-5)' },
  { value: 'Europe/London', label: 'Europe/London (GMT/BST, UTC+0/+1)' },
  { value: 'Europe/Paris', label: 'Europe/Paris (CET/CEST, UTC+1/+2)' },
  { value: 'Asia/Tokyo', label: 'Asia/Tokyo (JST, UTC+9)' },
  { value: 'Asia/Dubai', label: 'Asia/Dubai (GST, UTC+4)' },
  { value: 'Australia/Sydney', label: 'Australia/Sydney (AEST/AEDT, UTC+10/+11)' }
];

export default function CalendarPage() {
  const [viewMode, setViewMode] = useState<'month' | 'week' | 'day'>('month');
  const [currentDate, setCurrentDate] = useState<Date>(new Date());
  const [selectedTimezone, setSelectedTimezone] = useState<string>('UTC');
  const [events, setEvents] = useState<CalendarEventItem[]>([]);
  const [upcomingEvents, setUpcomingEvents] = useState<CalendarEventItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Detail / Reschedule Drawer State
  const [selectedEvent, setSelectedEvent] = useState<CalendarEventItem | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState<boolean>(false);
  const [rescheduleDate, setRescheduleDate] = useState<string>('');
  const [rescheduleTime, setRescheduleTime] = useState<string>('12:00');
  const [isRescheduling, setIsRescheduling] = useState<boolean>(false);
  const [isCancelling, setIsCancelling] = useState<boolean>(false);

  // Schedule Modal State
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState<boolean>(false);
  const [contents, setContents] = useState<ContentItem[]>([]);
  const [connections, setConnections] = useState<PlatformConnectionItem[]>([]);
  const [selectedContentId, setSelectedContentId] = useState<string>('');
  const [selectedVariantId, setSelectedVariantId] = useState<string>('');
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['youtube']);
  const [activeModalTab, setActiveModalTab] = useState<string>('youtube');
  const [scheduleDate, setScheduleDate] = useState<string>('');
  const [scheduleTime, setScheduleTime] = useState<string>('15:00');
  const [platformMetaMap, setPlatformMetaMap] = useState<Record<string, { connectionId: string; title: string; description: string; tags: string; privacy: 'PRIVATE' | 'UNLISTED' | 'PUBLIC' }>>({});
  const [isSubmittingSchedule, setIsSubmittingSchedule] = useState<boolean>(false);
  const [scheduleFeedback, setScheduleFeedback] = useState<string | null>(null);

  // Detect user timezone on mount
  useEffect(() => {
    try {
      const userTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (userTz) setSelectedTimezone(userTz);
    } catch {}

    // Pre-fill tomorrow as default schedule date
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    setScheduleDate(tomorrow.toISOString().split('T')[0]);
    setRescheduleDate(tomorrow.toISOString().split('T')[0]);
  }, []);

  // Compute view date range
  const dateRange = useMemo(() => {
    const start = new Date(currentDate);
    const end = new Date(currentDate);

    if (viewMode === 'month') {
      start.setDate(1);
      // Start from Monday of the week containing 1st
      const day = start.getDay();
      const diff = start.getDate() - day + (day === 0 ? -6 : 1);
      start.setDate(diff);

      end.setMonth(currentDate.getMonth() + 1);
      end.setDate(0); // last day of month
      // Extend to end of the week (Sunday)
      const endDay = end.getDay();
      if (endDay !== 0) {
        end.setDate(end.getDate() + (7 - endDay));
      }
    } else if (viewMode === 'week') {
      const day = start.getDay();
      const diff = start.getDate() - day + (day === 0 ? -6 : 1);
      start.setDate(diff);
      end.setDate(start.getDate() + 6);
    } else {
      // Day view
      start.setHours(0, 0, 0, 0);
      end.setHours(23, 59, 59, 999);
    }

    return {
      startStr: start.toISOString().split('T')[0],
      endStr: end.toISOString().split('T')[0],
      displayMonth: currentDate.toLocaleString('default', { month: 'long', year: 'numeric' })
    };
  }, [currentDate, viewMode]);

  // Load calendar events
  const loadCalendarEvents = async () => {
    try {
      setLoading(true);
      const res = await api.getCalendarEvents({
        start: dateRange.startStr,
        end: dateRange.endStr,
        timezone: selectedTimezone
      });
      setEvents(res.items || []);

      // Also load upcoming
      const now = new Date();
      const nextWeek = new Date();
      nextWeek.setDate(now.getDate() + 14);
      const upRes = await api.getCalendarEvents({
        start: now.toISOString().split('T')[0],
        end: nextWeek.toISOString().split('T')[0],
        timezone: selectedTimezone,
        status: 'SCHEDULED'
      });
      setUpcomingEvents(upRes.items || []);
    } catch (err: any) {
      setNotification({ type: 'error', message: 'Failed to load scheduled publications.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCalendarEvents();
  }, [dateRange, selectedTimezone]);

  // Load content and platform connections for modal
  const openScheduleModal = async () => {
    try {
      const [cntList, connList] = await Promise.all([
        api.getContentList(),
        api.getPlatformConnections()
      ]);
      setContents(cntList.items || []);
      setConnections(connList.items || []);

      if (cntList.items && cntList.items.length > 0) {
        const first = cntList.items[0];
        setSelectedContentId(first.id);
        if (first.variants && first.variants.length > 0) {
          setSelectedVariantId(first.variants[0].id);
        } else if (first.clips && first.clips.length > 0 && first.clips[0].variants && first.clips[0].variants.length > 0) {
          setSelectedVariantId(first.clips[0].variants[0].id);
        }
      }

      // Initialize platform map
      const initialPlatforms = ['youtube', 'instagram', 'linkedin', 'x', 'facebook', 'tiktok'];
      const newMap: Record<string, any> = {};
      initialPlatforms.forEach(p => {
        const conn = connList.items?.find((c: any) => c.platform.toLowerCase() === p && c.status === 'CONNECTED');
        newMap[p] = {
          connectionId: conn ? conn.id : '',
          title: 'Scheduled Social Post',
          description: 'Scheduled with Reflow automated calendar.',
          tags: 'reflow, schedule, viral',
          privacy: 'PRIVATE'
        };
      });

      setPlatformMetaMap(newMap);
      setSelectedPlatforms(['youtube']);
      setActiveModalTab('youtube');
      setScheduleFeedback(null);
      setIsScheduleModalOpen(true);
    } catch (err: any) {
      setNotification({ type: 'error', message: 'Failed to initialize scheduling modal.' });
    }
  };

  const handleConfirmSchedule = async () => {
    if (!selectedContentId || selectedPlatforms.length === 0) return;
    if (!scheduleDate || !scheduleTime) {
      setScheduleFeedback('Please specify both a target date and time.');
      return;
    }

    const isoLocal = `${scheduleDate}T${scheduleTime}:00`;
    const destinations = [];

    for (const p of selectedPlatforms) {
      const meta = platformMetaMap[p];
      if (!meta || !meta.connectionId) {
        setScheduleFeedback(`No connected account for ${p.toUpperCase()}. Select an account or deselect.`);
        return;
      }
      destinations.push({
        platform_connection_id: meta.connectionId,
        title: meta.title.trim(),
        description: meta.description.trim(),
        privacy: meta.privacy,
        tags: meta.tags.split(',').map((t: string) => t.trim()).filter(Boolean)
      });
    }

    setIsSubmittingSchedule(true);
    setScheduleFeedback(null);

    try {
      const res = await api.schedulePublications({
        content_id: selectedContentId,
        variant_id: selectedVariantId || undefined,
        scheduled_time: isoLocal,
        timezone: selectedTimezone,
        destinations: destinations
      });

      setNotification({
        type: 'success',
        message: `Successfully scheduled ${res.scheduled_count} publication(s) for ${scheduleDate} ${scheduleTime} (${selectedTimezone})!`
      });
      setIsScheduleModalOpen(false);
      await loadCalendarEvents();
    } catch (err: any) {
      setScheduleFeedback(`Scheduling failed: ${err.message}`);
    } finally {
      setIsSubmittingSchedule(false);
    }
  };

  const handleOpenDetail = (ev: CalendarEventItem) => {
    setSelectedEvent(ev);
    if (ev.scheduled_at_local) {
      const parts = ev.scheduled_at_local.split(' ');
      setRescheduleDate(parts[0] || '');
      setRescheduleTime(parts[1] ? parts[1].substring(0, 5) : '12:00');
    }
    setIsDetailOpen(true);
  };

  const handleReschedule = async () => {
    if (!selectedEvent) return;
    if (!rescheduleDate || !rescheduleTime) {
      alert('Please specify a new date and time.');
      return;
    }

    setIsRescheduling(true);
    try {
      const isoLocal = `${rescheduleDate}T${rescheduleTime}:00`;
      await api.reschedulePublication(selectedEvent.publication_id, {
        scheduled_time: isoLocal,
        timezone: selectedTimezone
      });
      setNotification({ type: 'success', message: 'Publication rescheduled successfully.' });
      setIsDetailOpen(false);
      await loadCalendarEvents();
    } catch (err: any) {
      alert(`Rescheduling failed: ${err.message}`);
    } finally {
      setIsRescheduling(false);
    }
  };

  const handleCancelPublication = async () => {
    if (!selectedEvent) return;
    if (!confirm('Are you sure you want to cancel this scheduled publication?')) return;

    setIsCancelling(true);
    try {
      await api.cancelPublication(selectedEvent.publication_id);
      setNotification({ type: 'success', message: 'Publication cancelled.' });
      setIsDetailOpen(false);
      await loadCalendarEvents();
    } catch (err: any) {
      alert(`Cancellation failed: ${err.message}`);
    } finally {
      setIsCancelling(false);
    }
  };

  const navigateDate = (dir: 'prev' | 'next' | 'today') => {
    const next = new Date(currentDate);
    if (dir === 'today') {
      setCurrentDate(new Date());
      return;
    }

    if (viewMode === 'month') {
      next.setMonth(next.getMonth() + (dir === 'next' ? 1 : -1));
    } else if (viewMode === 'week') {
      next.setDate(next.getDate() + (dir === 'next' ? 7 : -7));
    } else {
      next.setDate(next.getDate() + (dir === 'next' ? 1 : -1));
    }
    setCurrentDate(next);
  };

  const getPlatformIcon = (platform: string) => {
    switch (platform.toLowerCase()) {
      case 'youtube': return <YoutubeIcon className="w-4 h-4 text-red-400" />;
      case 'instagram': return <InstagramIcon className="w-4 h-4 text-pink-400" />;
      case 'linkedin': return <LinkedinIcon className="w-4 h-4 text-blue-400" />;
      case 'x': return <XIcon className="w-3.5 h-3.5 text-gray-300" />;
      case 'facebook': return <FacebookIcon className="w-4 h-4 text-blue-500" />;
      case 'tiktok': return <TiktokIcon className="w-4 h-4 text-cyan-400" />;
      default: return <Share2 className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'SCHEDULED':
        return <span className="text-[10px] font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">Scheduled</span>;
      case 'QUEUED':
        return <span className="text-[10px] font-bold text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/30">Queued</span>;
      case 'PUBLISHED':
        return <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30">Published</span>;
      case 'FAILED':
        return <span className="text-[10px] font-bold text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/30">Failed</span>;
      case 'CANCELLED':
        return <span className="text-[10px] font-bold text-gray-400 bg-gray-500/10 px-2 py-0.5 rounded border border-gray-500/30">Cancelled</span>;
      default:
        return <span className="text-[10px] font-bold text-gray-400 bg-gray-500/10 px-2 py-0.5 rounded">{status}</span>;
    }
  };

  // Generate day columns for Month & Week view
  const daysInGrid = useMemo(() => {
    const days = [];
    const current = new Date(dateRange.startStr);
    const end = new Date(dateRange.endStr);

    while (current <= end) {
      const dateKey = current.toISOString().split('T')[0];
      const isCurrentMonth = current.getMonth() === currentDate.getMonth();
      const isToday = dateKey === new Date().toISOString().split('T')[0];

      // Filter events on this day
      const dayEvents = events.filter(e => {
        const evDate = e.scheduled_at_local ? e.scheduled_at_local.split(' ')[0] : '';
        return evDate === dateKey;
      });

      days.push({
        date: new Date(current),
        dateKey,
        dayNum: current.getDate(),
        dayName: current.toLocaleString('default', { weekday: 'short' }),
        isCurrentMonth,
        isToday,
        events: dayEvents
      });

      current.setDate(current.getDate() + 1);
    }
    return days;
  }, [dateRange, events, currentDate]);

  return (
    <div className="space-y-6 animate-fadeIn pb-16">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <CalendarDays className="w-6 h-6 text-indigo-400" />
            <span>Content Scheduler & Calendar</span>
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Real server-side scheduling engine. Publications persist in PostgreSQL and dispatch through Redis background workers.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Timezone Selector */}
          <div className="flex items-center gap-1.5 bg-[#111827] border border-[#1F2937] px-3 py-1.5 rounded-xl text-xs text-gray-300">
            <Clock className="w-3.5 h-3.5 text-indigo-400" />
            <select
              value={selectedTimezone}
              onChange={(e) => setSelectedTimezone(e.target.value)}
              className="bg-transparent text-white font-medium focus:outline-none cursor-pointer"
            >
              {COMMON_TIMEZONES.map(tz => (
                <option key={tz.value} value={tz.value} className="bg-[#111827] text-white">
                  {tz.label}
                </option>
              ))}
            </select>
          </div>

          {/* Schedule Post CTA */}
          <button
            onClick={openScheduleModal}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-bold shadow-md shadow-indigo-600/30 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Schedule Post</span>
          </button>
        </div>
      </div>

      {/* Notification */}
      {notification && (
        <div className={`p-4 rounded-xl flex items-center justify-between border ${
          notification.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-red-500/10 border-red-500/30 text-red-300'
        }`}>
          <div className="flex items-center gap-2 text-xs">
            {notification.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
            <span>{notification.message}</span>
          </div>
          <button onClick={() => setNotification(null)} className="text-xs hover:underline opacity-80">
            Dismiss
          </button>
        </div>
      )}

      {/* Main Calendar View Container */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Calendar Grid (3 Columns) */}
        <div className="lg:col-span-3 bg-[#111827] border border-[#1F2937] rounded-2xl overflow-hidden shadow-xl flex flex-col">
          {/* Calendar Toolbar */}
          <div className="p-4 border-b border-[#1F2937] flex flex-wrap items-center justify-between gap-3 bg-[#161B26]">
            <div className="flex items-center gap-3">
              <h2 className="text-base font-bold text-white">
                {dateRange.displayMonth}
              </h2>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => navigateDate('prev')}
                  className="p-1.5 rounded-lg bg-[#111827] hover:bg-[#1F2937] text-gray-400 hover:text-white border border-[#1F2937] transition"
                  title="Previous"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => navigateDate('today')}
                  className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-[#111827] hover:bg-[#1F2937] text-gray-300 hover:text-white border border-[#1F2937] transition"
                >
                  Today
                </button>
                <button
                  onClick={() => navigateDate('next')}
                  className="p-1.5 rounded-lg bg-[#111827] hover:bg-[#1F2937] text-gray-400 hover:text-white border border-[#1F2937] transition"
                  title="Next"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* View Mode Switcher */}
            <div className="flex items-center gap-1 bg-[#111827] p-1 rounded-xl border border-[#1F2937]">
              {(['month', 'week', 'day'] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setViewMode(mode)}
                  className={`px-3 py-1 rounded-lg text-xs font-bold uppercase tracking-wider transition-all ${
                    viewMode === mode
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>
          </div>

          {/* Weekday Headers */}
          <div className="grid grid-cols-7 border-b border-[#1F2937] text-center bg-[#0F141E] text-xs font-bold text-gray-400 py-2">
            {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => (
              <div key={day}>{day}</div>
            ))}
          </div>

          {/* Month / Week Grid Days */}
          <div className="grid grid-cols-7 min-h-[560px] divide-x divide-y divide-[#1F2937] bg-[#0B0D12]">
            {daysInGrid.map((cell) => (
              <div
                key={cell.dateKey}
                className={`p-2 min-h-[110px] space-y-1.5 transition-colors ${
                  cell.isCurrentMonth ? 'bg-[#0B0D12]' : 'bg-[#08090C]/60 text-gray-600'
                } ${cell.isToday ? 'ring-1 ring-inset ring-indigo-500/50 bg-indigo-950/10' : ''}`}
              >
                <div className="flex items-center justify-between">
                  <span
                    className={`text-xs font-mono font-bold rounded-full w-5 h-5 flex items-center justify-center ${
                      cell.isToday
                        ? 'bg-indigo-600 text-white'
                        : cell.isCurrentMonth
                        ? 'text-gray-300'
                        : 'text-gray-600'
                    }`}
                  >
                    {cell.dayNum}
                  </span>
                  {cell.events.length > 0 && (
                    <span className="text-[10px] font-bold text-gray-500">
                      {cell.events.length} post{cell.events.length > 1 ? 's' : ''}
                    </span>
                  )}
                </div>

                {/* Event Pills */}
                <div className="space-y-1 overflow-y-auto max-h-[100px] pr-0.5">
                  {cell.events.map((ev) => {
                    const timePart = ev.scheduled_at_local ? ev.scheduled_at_local.split(' ')[1]?.substring(0, 5) : '';
                    return (
                      <div
                        key={ev.id}
                        onClick={() => handleOpenDetail(ev)}
                        className="p-1.5 rounded-lg bg-[#161B26] hover:bg-[#1F2937] border border-[#1F2937] cursor-pointer text-xs space-y-1 transition shadow-sm"
                      >
                        <div className="flex items-center justify-between gap-1">
                          <div className="flex items-center gap-1 truncate">
                            {getPlatformIcon(ev.platform)}
                            <span className="text-[11px] font-bold text-white truncate">
                              {ev.title || ev.content_title}
                            </span>
                          </div>
                          <span className="text-[9px] font-mono text-gray-400 shrink-0">
                            {timePart}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-[9px] text-gray-400 truncate max-w-[80px]">
                            {ev.account_name || ev.handle || ev.platform}
                          </span>
                          {getStatusBadge(ev.status)}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Upcoming Posts Sidebar (1 Column) */}
        <div className="space-y-4">
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-[#1F2937] pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Clock className="w-4 h-4 text-indigo-400" />
                <span>Upcoming Posts</span>
              </h3>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                Server-Side Active
              </span>
            </div>

            {upcomingEvents.length === 0 ? (
              <div className="py-8 text-center space-y-2">
                <CalendarIcon className="w-8 h-8 text-gray-600 mx-auto" />
                <p className="text-xs text-gray-400 font-medium">No upcoming scheduled posts.</p>
                <button
                  onClick={openScheduleModal}
                  className="text-xs text-indigo-400 hover:text-indigo-300 font-bold hover:underline"
                >
                  Schedule one now →
                </button>
              </div>
            ) : (
              <div className="space-y-2.5 max-h-[500px] overflow-y-auto pr-1">
                {upcomingEvents.map((ev) => (
                  <div
                    key={ev.id}
                    onClick={() => handleOpenDetail(ev)}
                    className="p-3 bg-[#161B26] hover:bg-[#1F2937] border border-[#1F2937] rounded-xl cursor-pointer space-y-2 transition"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        {getPlatformIcon(ev.platform)}
                        <span className="text-xs font-bold text-white truncate max-w-[130px]">
                          {ev.title || ev.content_title}
                        </span>
                      </div>
                      {getStatusBadge(ev.status)}
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-gray-400 font-mono">
                      <span>{ev.scheduled_at_local}</span>
                      <span className="text-gray-500">{ev.timezone}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Schedule Post Modal */}
      {isScheduleModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-fadeIn">
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl w-full max-w-2xl p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#1F2937] pb-3">
              <div className="flex items-center gap-2 text-white font-bold text-base">
                <CalendarDays className="w-5 h-5 text-indigo-400" />
                <span>Schedule Multi-Platform Post</span>
              </div>
              <button onClick={() => setIsScheduleModalOpen(false)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {scheduleFeedback && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-xs text-red-300">
                {scheduleFeedback}
              </div>
            )}

            <div className="space-y-4 text-xs">
              {/* 1. Content & Variant Picker */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-gray-400 font-medium block mb-1">Source Content Asset</label>
                  <select
                    value={selectedContentId}
                    onChange={(e) => {
                      setSelectedContentId(e.target.value);
                      const c = contents.find(x => x.id === e.target.value);
                      if (c && c.variants && c.variants.length > 0) {
                        setSelectedVariantId(c.variants[0].id);
                      }
                    }}
                    className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl px-3 py-2 text-white font-medium focus:outline-none focus:border-indigo-500"
                  >
                    {contents.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.title} ({c.content_type})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-gray-400 font-medium block mb-1">Date & Timezone</label>
                  <div className="flex items-center gap-1.5">
                    <input
                      type="date"
                      value={scheduleDate}
                      onChange={(e) => setScheduleDate(e.target.value)}
                      className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl px-3 py-2 text-white font-medium focus:outline-none focus:border-indigo-500 font-mono text-xs"
                    />
                    <input
                      type="time"
                      value={scheduleTime}
                      onChange={(e) => setScheduleTime(e.target.value)}
                      className="w-28 bg-[#161B26] border border-[#1F2937] rounded-xl px-3 py-2 text-white font-medium focus:outline-none focus:border-indigo-500 font-mono text-xs"
                    />
                  </div>
                </div>
              </div>

              {/* 2. Platform Destination Selector */}
              <div className="space-y-1.5">
                <label className="text-gray-400 font-medium block">Target Social Destinations</label>
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                  {[
                    { id: 'youtube', label: 'YouTube', icon: YoutubeIcon },
                    { id: 'instagram', label: 'Instagram', icon: InstagramIcon },
                    { id: 'linkedin', label: 'LinkedIn', icon: LinkedinIcon },
                    { id: 'x', label: 'X', icon: XIcon },
                    { id: 'facebook', label: 'Facebook', icon: FacebookIcon },
                    { id: 'tiktok', label: 'TikTok', icon: TiktokIcon }
                  ].map((p) => {
                    const Icon = p.icon;
                    const isSelected = selectedPlatforms.includes(p.id);
                    const isConnected = connections.some(c => c.platform.toLowerCase() === p.id && c.status === 'CONNECTED');

                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => {
                          if (isSelected) {
                            if (selectedPlatforms.length > 1) {
                              setSelectedPlatforms(prev => prev.filter(x => x !== p.id));
                              if (activeModalTab === p.id) {
                                const remaining = selectedPlatforms.filter(x => x !== p.id);
                                setActiveModalTab(remaining[0] || 'youtube');
                              }
                            }
                          } else {
                            setSelectedPlatforms(prev => [...prev, p.id]);
                            setActiveModalTab(p.id);
                          }
                        }}
                        className={`p-2.5 rounded-xl border flex flex-col items-center gap-1.5 transition text-xs font-semibold ${
                          isSelected
                            ? 'bg-indigo-600/20 border-indigo-500 text-white shadow-md'
                            : isConnected
                            ? 'bg-[#161B26] border-[#1F2937] text-gray-300'
                            : 'bg-[#161B26]/50 border-dashed border-gray-800 text-gray-500'
                        }`}
                      >
                        <Icon className="w-4 h-4" />
                        <span className="text-[11px]">{p.label}</span>
                        {isSelected ? (
                          <CheckCircle2 className="w-3 h-3 text-indigo-400" />
                        ) : isConnected ? (
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                        ) : (
                          <span className="text-[8px] text-amber-400 font-mono">Connect</span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 3. Destination Specific Metadata */}
              <div className="space-y-3 bg-[#161B26] border border-[#1F2937] rounded-xl p-4">
                <div className="flex items-center justify-between border-b border-[#1F2937] pb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-gray-300">Customize Copy:</span>
                    <div className="flex items-center gap-1">
                      {selectedPlatforms.map(p => (
                        <button
                          key={p}
                          type="button"
                          onClick={() => setActiveModalTab(p)}
                          className={`px-2.5 py-1 rounded-lg text-[11px] font-bold uppercase tracking-wider transition ${
                            activeModalTab === p
                              ? 'bg-indigo-600 text-white'
                              : 'text-gray-400 hover:text-white bg-[#111827]'
                          }`}
                        >
                          {p}
                        </button>
                      ))}
                    </div>
                  </div>
                  <span className="text-[10px] font-mono text-emerald-400">
                    IANA: {selectedTimezone}
                  </span>
                </div>

                {(() => {
                  const p = activeModalTab;
                  const meta = platformMetaMap[p] || { connectionId: '', title: '', description: '', tags: '', privacy: 'PRIVATE' };
                  const matchingConns = connections.filter(c => c.platform.toLowerCase() === p && c.status === 'CONNECTED');

                  return (
                    <div className="space-y-3 text-xs">
                      <div>
                        <label className="text-gray-400 font-medium block mb-1">Target Account</label>
                        {matchingConns.length > 0 ? (
                          <select
                            value={meta.connectionId}
                            onChange={(e) => {
                              const val = e.target.value;
                              setPlatformMetaMap(prev => ({ ...prev, [p]: { ...meta, connectionId: val } }));
                            }}
                            className="w-full bg-[#111827] border border-[#1F2937] rounded-xl px-3 py-2 text-white font-medium"
                          >
                            {matchingConns.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.account_name} ({c.handle || c.name})
                              </option>
                            ))}
                          </select>
                        ) : (
                          <div className="p-2.5 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-center justify-between text-amber-300 text-[11px]">
                            <span>No connected {p.toUpperCase()} account.</span>
                            <a href="/connections" className="underline font-bold text-white">Connect</a>
                          </div>
                        )}
                      </div>

                      {['youtube', 'linkedin', 'facebook', 'tiktok'].includes(p) && (
                        <div>
                          <label className="text-gray-400 font-medium block mb-1">Title</label>
                          <input
                            type="text"
                            value={meta.title}
                            onChange={(e) => {
                              const val = e.target.value;
                              setPlatformMetaMap(prev => ({ ...prev, [p]: { ...meta, title: val } }));
                            }}
                            className="w-full bg-[#111827] border border-[#1F2937] rounded-xl px-3 py-2 text-white"
                          />
                        </div>
                      )}

                      <div>
                        <label className="text-gray-400 font-medium block mb-1">
                          {p === 'x' ? 'Tweet Text (max 280)' : 'Caption & Description'}
                        </label>
                        <textarea
                          rows={3}
                          maxLength={p === 'x' ? 280 : 5000}
                          value={meta.description}
                          onChange={(e) => {
                            const val = e.target.value;
                            setPlatformMetaMap(prev => ({ ...prev, [p]: { ...meta, description: val } }));
                          }}
                          className="w-full bg-[#111827] border border-[#1F2937] rounded-xl p-2.5 text-white font-mono text-[11px] resize-none"
                        />
                      </div>
                    </div>
                  );
                })()}
              </div>
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-between pt-3 border-t border-[#1F2937]">
              <span className="text-[11px] text-gray-500 flex items-center gap-1">
                <Lock className="w-3 h-3 text-emerald-400" />
                <span>UTC Authority Engine</span>
              </span>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsScheduleModalOpen(false)}
                  className="px-3.5 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-semibold transition"
                >
                  Cancel
                </button>

                <button
                  onClick={handleConfirmSchedule}
                  disabled={isSubmittingSchedule || selectedPlatforms.length === 0}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-md shadow-indigo-600/30 transition disabled:opacity-50 cursor-pointer"
                >
                  {isSubmittingSchedule ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <CalendarIcon className="w-3.5 h-3.5" />}
                  <span>{isSubmittingSchedule ? "Persisting Schedule..." : `Schedule (${selectedPlatforms.length} Destinations)`}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Event Detail & Reschedule Drawer */}
      {isDetailOpen && selectedEvent && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-fadeIn">
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl w-full max-w-lg p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#1F2937] pb-3">
              <div className="flex items-center gap-2.5 text-white font-bold text-base">
                {getPlatformIcon(selectedEvent.platform)}
                <span className="capitalize">{selectedEvent.platform} Publication</span>
              </div>
              <button onClick={() => setIsDetailOpen(false)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="bg-[#161B26] p-3.5 rounded-xl border border-[#1F2937] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Content:</span>
                  <span className="font-bold text-white">{selectedEvent.content_title}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Account:</span>
                  <span className="font-mono text-gray-200">{selectedEvent.account_name || selectedEvent.handle || 'Default Account'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Status:</span>
                  <div>{getStatusBadge(selectedEvent.status)}</div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Scheduled Time:</span>
                  <span className="font-mono text-indigo-300 font-bold">{selectedEvent.scheduled_at_local} ({selectedEvent.timezone})</span>
                </div>
                {selectedEvent.external_url && (
                  <div className="flex items-center justify-between pt-1 border-t border-[#1F2937]">
                    <span className="text-gray-400">Live Post:</span>
                    <a
                      href={selectedEvent.external_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-indigo-400 hover:underline flex items-center gap-1 font-bold"
                    >
                      <span>View on {selectedEvent.platform}</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                )}
              </div>

              {/* Reschedule Section (if in SCHEDULED state) */}
              {selectedEvent.status === 'SCHEDULED' && (
                <div className="space-y-2 pt-2 border-t border-[#1F2937]">
                  <label className="text-xs font-bold text-gray-300 block">Reschedule Publication</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="date"
                      value={rescheduleDate}
                      onChange={(e) => setRescheduleDate(e.target.value)}
                      className="w-full bg-[#161B26] border border-[#1F2937] rounded-xl px-3 py-2 text-white font-mono text-xs"
                    />
                    <input
                      type="time"
                      value={rescheduleTime}
                      onChange={(e) => setRescheduleTime(e.target.value)}
                      className="w-28 bg-[#161B26] border border-[#1F2937] rounded-xl px-3 py-2 text-white font-mono text-xs"
                    />
                    <button
                      onClick={handleReschedule}
                      disabled={isRescheduling}
                      className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold transition flex items-center gap-1"
                    >
                      {isRescheduling && <RefreshCw className="w-3 h-3 animate-spin" />}
                      <span>Save</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-[#1F2937]">
              {selectedEvent.status === 'SCHEDULED' ? (
                <button
                  onClick={handleCancelPublication}
                  disabled={isCancelling}
                  className="px-3 py-1.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 text-xs font-bold transition"
                >
                  {isCancelling ? "Cancelling..." : "Cancel Schedule"}
                </button>
              ) : (
                <div />
              )}

              <button
                onClick={() => setIsDetailOpen(false)}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-xl text-xs font-semibold transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
