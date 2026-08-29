"use client";

import React, { useState } from 'react';
import { Search, Bell, Plus, Sparkles } from 'lucide-react';
import Link from 'next/link';

export const Header: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <header className="h-16 border-b border-[#1F2937]/70 bg-[#0B0D12]/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-20">
      {/* Search Bar */}
      <div className="relative w-96">
        <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search content, workflows, tags... (Cmd + K)"
          className="w-full bg-[#161B26] border border-[#1F2937] focus:border-indigo-500 rounded-xl pl-9 pr-4 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all"
        />
      </div>

      {/* Right Action Icons */}
      <div className="flex items-center gap-3">
        <button className="p-2 text-gray-400 hover:text-white rounded-xl hover:bg-[#161B26] transition-colors relative">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-indigo-500" />
        </button>

        <Link
          href="/repurpose"
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-medium shadow-md shadow-indigo-600/20 transition-all active:scale-95"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>New Repurpose</span>
        </Link>
      </div>
    </header>
  );
};
