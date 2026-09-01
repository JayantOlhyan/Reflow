"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Search, Command, X, Video, Layers, Calendar, Sparkles, Settings, Shield, FileText, ArrowRight } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { SearchResultItem } from '@/types';
import { api } from '@/lib/api';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
      setResults([]);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setLoading(true);
        const res = await api.searchEntities(query.trim());
        setResults(res.results || []);
        setSelectedIndex(0);
      } catch (e) {
        console.warn("Global search failed:", e);
      } finally {
        setLoading(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [query]);

  const quickNavItems = [
    { title: 'Content Library', url: '/content', icon: <Video className="w-4 h-4 text-indigo-400" /> },
    { title: 'Approvals Center', url: '/approvals', icon: <Shield className="w-4 h-4 text-emerald-400" /> },
    { title: 'Publishing Queue', url: '/publishing', icon: <Layers className="w-4 h-4 text-blue-400" /> },
    { title: 'Content Calendar', url: '/calendar', icon: <Calendar className="w-4 h-4 text-purple-400" /> },
    { title: 'Repurpose Studio', url: '/repurpose', icon: <Sparkles className="w-4 h-4 text-amber-400" /> },
    { title: 'System Settings', url: '/settings', icon: <Settings className="w-4 h-4 text-slate-400" /> }
  ];

  const handleSelect = (url: string) => {
    onClose();
    router.push(url);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      const maxIndex = query ? results.length - 1 : quickNavItems.length - 1;
      setSelectedIndex(prev => (prev < maxIndex ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      const maxIndex = query ? results.length - 1 : quickNavItems.length - 1;
      setSelectedIndex(prev => (prev > 0 ? prev - 1 : maxIndex));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (query && results[selectedIndex]) {
        handleSelect(results[selectedIndex].url);
      } else if (!query && quickNavItems[selectedIndex]) {
        handleSelect(quickNavItems[selectedIndex].url);
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/70 backdrop-blur-md p-4 sm:p-6 md:p-20 flex justify-center items-start">
      <div
        className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col transform transition-all"
        onKeyDown={handleKeyDown}
      >
        {/* Input Bar */}
        <div className="relative border-b border-slate-800 flex items-center px-4">
          <Search className="w-5 h-5 text-slate-400 mr-3 flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search content, clips, carousels, publications, automations... (Cmd+K)"
            className="w-full py-4 bg-transparent text-white placeholder-slate-500 focus:outline-none text-base font-normal"
          />
          {query ? (
            <button onClick={() => setQuery('')} className="p-1 text-slate-400 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          ) : (
            <kbd className="hidden sm:inline-block px-2 py-0.5 text-xs text-slate-400 bg-slate-800 border border-slate-700 rounded font-mono">
              ESC
            </kbd>
          )}
        </div>

        {/* Results / Navigation */}
        <div className="max-h-96 overflow-y-auto p-2">
          {loading ? (
            <div className="py-8 text-center text-sm text-slate-500">Searching workspace...</div>
          ) : query ? (
            results.length === 0 ? (
              <div className="py-8 text-center text-sm text-slate-500">No matching results found for "{query}".</div>
            ) : (
              <div className="space-y-1">
                <div className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  Search Results ({results.length})
                </div>
                {results.map((item, idx) => (
                  <button
                    key={`${item.type}-${item.id}`}
                    onClick={() => handleSelect(item.url)}
                    className={`w-full text-left px-3 py-2.5 rounded-xl flex items-center justify-between transition ${
                      idx === selectedIndex ? 'bg-indigo-600/20 border border-indigo-500/40 text-white' : 'text-slate-300 hover:bg-slate-800/60'
                    }`}
                  >
                    <div className="flex items-center space-x-3 min-w-0">
                      <div className="p-2 rounded-lg bg-slate-800 text-slate-300">
                        <FileText className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">{item.title}</div>
                        <div className="text-xs text-slate-400 truncate">{item.subtitle}</div>
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-slate-500 flex-shrink-0 ml-2" />
                  </button>
                ))}
              </div>
            )
          ) : (
            <div className="space-y-1">
              <div className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                Quick Navigation
              </div>
              {quickNavItems.map((item, idx) => (
                <button
                  key={item.url}
                  onClick={() => handleSelect(item.url)}
                  className={`w-full text-left px-3 py-2.5 rounded-xl flex items-center justify-between transition ${
                    idx === selectedIndex ? 'bg-indigo-600/20 border border-indigo-500/40 text-white' : 'text-slate-300 hover:bg-slate-800/60'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <div className="p-2 rounded-lg bg-slate-800">{item.icon}</div>
                    <span className="text-sm font-medium">{item.title}</span>
                  </div>
                  <kbd className="text-[10px] text-slate-500 font-mono">Jump →</kbd>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
