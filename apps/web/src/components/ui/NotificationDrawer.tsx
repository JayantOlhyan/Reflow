"use client";

import React, { useState, useEffect } from 'react';
import { Bell, X, CheckCheck, AlertTriangle, CheckCircle, Info, XCircle, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { NotificationItem } from '@/types';
import { api } from '@/lib/api';

interface NotificationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function NotificationDrawer({ isOpen, onClose }: NotificationDrawerProps) {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (isOpen) {
      loadNotifications();
    }
  }, [isOpen]);

  const loadNotifications = async () => {
    try {
      setLoading(true);
      const res = await api.getNotifications(50);
      setNotifications(res.items || []);
      setUnreadCount(res.unread_count || 0);
    } catch (e) {
      console.warn("Failed to load notifications:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkRead = async (id: string) => {
    try {
      await api.markNotificationRead(id);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (e) {
      console.warn("Failed to mark read:", e);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch (e) {
      console.warn("Failed to mark all read:", e);
    }
  };

  if (!isOpen) return null;

  const getSeverityIcon = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'SUCCESS': return <CheckCircle className="w-5 h-5 text-emerald-400" />;
      case 'WARNING': return <AlertTriangle className="w-5 h-5 text-amber-400" />;
      case 'ERROR': return <XCircle className="w-5 h-5 text-rose-400" />;
      default: return <Info className="w-5 h-5 text-indigo-400" />;
    }
  };

  const getEntityUrl = (item: NotificationItem) => {
    if (!item.entity_type || !item.entity_id) return null;
    switch (item.entity_type.toLowerCase()) {
      case 'content': return `/content/${item.entity_id}`;
      case 'clip': return `/content/${item.entity_id}?tab=clips`;
      case 'carousel': return `/content/${item.entity_id}?tab=carousels`;
      case 'publication': return `/publishing?id=${item.entity_id}`;
      case 'experiment': return `/experiments?id=${item.entity_id}`;
      case 'automation': return `/automations?id=${item.entity_id}`;
      default: return null;
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-950/60 backdrop-blur-sm transition-opacity">
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col">
          {/* Header */}
          <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/80 backdrop-blur">
            <div className="flex items-center space-x-2">
              <Bell className="w-5 h-5 text-indigo-400" />
              <h2 className="text-lg font-semibold text-white">Notifications</h2>
              {unreadCount > 0 && (
                <span className="px-2 py-0.5 text-xs font-medium bg-indigo-500/20 text-indigo-300 rounded-full border border-indigo-500/30">
                  {unreadCount} new
                </span>
              )}
            </div>
            <div className="flex items-center space-x-2">
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="p-1.5 text-xs text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition flex items-center gap-1"
                  title="Mark all as read"
                >
                  <CheckCheck className="w-4 h-4" />
                  <span className="hidden sm:inline">Mark all read</span>
                </button>
              )}
              <button
                onClick={onClose}
                className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {loading ? (
              <div className="text-center py-12 text-slate-500">Loading notifications...</div>
            ) : notifications.length === 0 ? (
              <div className="text-center py-16 text-slate-500">
                <Bell className="w-10 h-10 mx-auto mb-3 opacity-30 text-slate-400" />
                <p className="text-sm">No notifications yet.</p>
              </div>
            ) : (
              notifications.map((n) => {
                const targetUrl = getEntityUrl(n);
                return (
                  <div
                    key={n.id}
                    className={`p-3.5 rounded-xl border transition flex gap-3 ${
                      n.read
                        ? 'bg-slate-900/40 border-slate-850 opacity-75'
                        : 'bg-slate-850/80 border-slate-750 shadow-sm'
                    }`}
                  >
                    <div className="mt-0.5 flex-shrink-0">{getSeverityIcon(n.severity)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="text-sm font-medium text-white truncate">{n.title}</h4>
                        <span className="text-[10px] text-slate-500 whitespace-nowrap">
                          {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">{n.message}</p>
                      
                      <div className="mt-2.5 flex items-center justify-between">
                        {targetUrl ? (
                          <Link
                            href={targetUrl}
                            onClick={onClose}
                            className="inline-flex items-center text-xs font-medium text-indigo-400 hover:text-indigo-300 gap-1 group"
                          >
                            View details
                            <ArrowRight className="w-3 h-3 transition-transform group-hover:translate-x-0.5" />
                          </Link>
                        ) : <span />}

                        {!n.read && (
                          <button
                            onClick={() => handleMarkRead(n.id)}
                            className="text-[11px] text-slate-500 hover:text-slate-300 transition"
                          >
                            Mark read
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
