"use client";

import React, { useState, useEffect } from 'react';
import { Search, Bell, Plus, Sparkles } from 'lucide-react';
import Link from 'next/link';
import NotificationDrawer from '@/components/ui/NotificationDrawer';
import CommandPalette from '@/components/ui/CommandPalette';
import QuickCreateModal from '@/components/ui/QuickCreateModal';
import { api } from '@/lib/api';

export const Header: React.FC = () => {
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [isCommandOpen, setIsCommandOpen] = useState(false);
  const [isQuickCreateOpen, setIsQuickCreateOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState<number>(0);

  useEffect(() => {
    fetchUnread();
    const interval = setInterval(fetchUnread, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsCommandOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const fetchUnread = async () => {
    try {
      const res = await api.getNotifications(10);
      setUnreadCount(res.unread_count || 0);
    } catch {
      // Ignore background notification fetch errors
    }
  };

  return (
    <>
      <header className="h-16 border-b border-[#1F2937]/70 bg-[#0B0D12]/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-20">
        {/* Search Command Palette Trigger */}
        <button
          onClick={() => setIsCommandOpen(true)}
          className="relative w-80 sm:w-96 bg-[#161B26] border border-[#1F2937] hover:border-indigo-500/50 rounded-xl pl-9 pr-4 py-1.5 text-xs text-left text-gray-400 hover:text-gray-300 flex items-center justify-between transition-all"
        >
          <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <span>Search workspace...</span>
          <kbd className="px-2 py-0.5 text-[10px] bg-slate-800 border border-slate-700 rounded font-mono text-slate-400">
            ⌘K
          </kbd>
        </button>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsNotificationOpen(true)}
            className="p-2 text-gray-400 hover:text-white rounded-xl hover:bg-[#161B26] transition-colors relative"
            title="Notifications"
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 px-1.5 py-0.5 text-[9px] font-bold rounded-full bg-indigo-500 text-white min-w-[16px] text-center">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setIsQuickCreateOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-medium transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create</span>
          </button>

          <Link
            href="/repurpose"
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-medium shadow-md shadow-indigo-600/20 transition-all active:scale-95"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Repurpose Studio</span>
          </Link>
        </div>
      </header>

      {/* Modals & Drawers */}
      <NotificationDrawer isOpen={isNotificationOpen} onClose={() => setIsNotificationOpen(false)} />
      <CommandPalette isOpen={isCommandOpen} onClose={() => setIsCommandOpen(false)} />
      <QuickCreateModal isOpen={isQuickCreateOpen} onClose={() => setIsQuickCreateOpen(false)} />
    </>
  );
};
