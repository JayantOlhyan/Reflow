"use client";

import React, { useState } from 'react';
import { 
  Plus
} from 'lucide-react';

export default function CalendarPage() {
  const [viewMode, setViewMode] = useState<'week' | 'month'>('week');

  const daysOfWeek = ['Mon 26', 'Tue 27', 'Wed 28', 'Thu 29', 'Fri 30', 'Sat 31', 'Sun 01'];

  const scheduledEvents = [
    {
      id: 'e1',
      day: 'Tue 27',
      time: '10:00',
      title: 'Instagram Reel',
      subtitle: 'Building in public Day 20',
      platform: 'instagram',
      color: 'bg-purple-600/30 text-purple-300 border-purple-500/40'
    },
    {
      id: 'e2',
      day: 'Tue 27',
      time: '14:30',
      title: 'YouTube Short',
      subtitle: 'System Design 101',
      platform: 'youtube',
      color: 'bg-red-600/30 text-red-300 border-red-500/40'
    },
    {
      id: 'e3',
      day: 'Thu 29',
      time: '11:30',
      title: 'LinkedIn Post',
      subtitle: 'Lessons from 24h build',
      platform: 'linkedin',
      color: 'bg-blue-600/30 text-blue-300 border-blue-500/40'
    },
    {
      id: 'e4',
      day: 'Thu 29',
      time: '16:00',
      title: 'TikTok Video',
      subtitle: 'Quick dev tips',
      platform: 'tiktok',
      color: 'bg-cyan-600/30 text-cyan-300 border-cyan-500/40'
    },
    {
      id: 'e5',
      day: 'Sat 31',
      time: '20:00',
      title: 'X Thread',
      subtitle: 'Why self-hosted wins',
      platform: 'x',
      color: 'bg-gray-700/50 text-gray-200 border-gray-600'
    },
    {
      id: 'e6',
      day: 'Sun 01',
      time: '18:00',
      title: 'Carousel Deck',
      subtitle: 'Automate Workflow',
      platform: 'instagram',
      color: 'bg-purple-600/30 text-purple-300 border-purple-500/40'
    }
  ];

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-white tracking-tight">Content Scheduler</h1>
          <span className="text-xs font-semibold text-gray-400 bg-[#161B26] px-3 py-1 rounded-xl border border-[#1F2937]">
            August 2026
          </span>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-[#111827] p-1 rounded-xl border border-[#1F2937]">
            <button
              onClick={() => setViewMode('week')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                viewMode === 'week' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              Week
            </button>
            <button
              onClick={() => setViewMode('month')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                viewMode === 'month' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              Month
            </button>
          </div>

          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-md transition-all">
            <Plus className="w-3.5 h-3.5" />
            <span>Schedule Post</span>
          </button>
        </div>
      </div>

      <div className="bg-[#111827] border border-[#1F2937] rounded-2xl overflow-hidden shadow-xl">
        <div className="grid grid-cols-7 border-b border-[#1F2937] text-center bg-[#161B26]">
          {daysOfWeek.map((day) => (
            <div key={day} className="py-3 px-2 text-xs font-bold text-gray-300 border-r border-[#1F2937] last:border-r-0">
              {day}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-7 min-h-[500px] divide-x divide-[#1F2937] bg-[#0B0D12]">
          {daysOfWeek.map((day) => {
            const eventsInDay = scheduledEvents.filter((e) => e.day === day);
            return (
              <div key={day} className="p-2 space-y-2.5 min-h-[480px] hover:bg-[#161B26]/30 transition-colors">
                {eventsInDay.map((ev) => (
                  <div
                    key={ev.id}
                    className={`p-3 rounded-xl border ${ev.color} cursor-pointer hover:scale-[1.02] transition-transform shadow-md`}
                  >
                    <div className="flex items-center justify-between text-[10px] opacity-80 mb-1">
                      <span className="font-mono">{ev.time}</span>
                      <span className="capitalize">{ev.platform}</span>
                    </div>
                    <h5 className="text-xs font-bold text-white truncate">{ev.title}</h5>
                    <p className="text-[10px] text-gray-300 truncate mt-0.5">{ev.subtitle}</p>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-4 pt-2 text-xs text-gray-400">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
            <span>Instagram</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
            <span>YouTube</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-500" />
            <span>TikTok</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
            <span>LinkedIn</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-gray-400" />
            <span>X (Twitter)</span>
          </div>
        </div>
        <span>Timezone: Local (Asia/Kolkata)</span>
      </div>
    </div>
  );
}
