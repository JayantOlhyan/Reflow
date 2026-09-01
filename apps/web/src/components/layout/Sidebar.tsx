"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Logo } from '../ui/Logo';
import {
  LayoutDashboard,
  FolderOpen,
  Sparkles,
  GitBranch,
  Calendar,
  Share2,
  BarChart3,
  Lightbulb,
  Settings,
  FileText,
  Layers,
  Activity,
  ShieldCheck,
  Puzzle
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  const mainNavItems = [
    { name: 'Overview', href: '/', icon: LayoutDashboard },
    { name: 'Content', href: '/content', icon: FolderOpen },
    { name: 'Approvals', href: '/approvals', icon: ShieldCheck },
    { name: 'Publishing', href: '/publishing', icon: Layers },
    { name: 'Repurpose', href: '/repurpose', icon: Sparkles },
    { name: 'Carousel', href: '/carousel', icon: Layers },
    { name: 'Workflows', href: '/workflows', icon: GitBranch },
    { name: 'Calendar', href: '/calendar', icon: Calendar },
    { name: 'Connections', href: '/connections', icon: Share2 },
    { name: 'Plugins', href: '/plugins', icon: Puzzle },
    { name: 'Analytics', href: '/analytics', icon: BarChart3 },
    { name: 'Intelligence', href: '/intelligence', icon: Lightbulb },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  const systemNavItems = [
    { name: 'Setup', href: '/setup', icon: ShieldCheck },
    { name: 'Logs', href: '/system?tab=logs', icon: FileText },
    { name: 'Jobs', href: '/system?tab=jobs', icon: Layers },
    { name: 'Health', href: '/system?tab=health', icon: Activity, badge: 'healthy' },
  ];

  return (
    <aside className="w-64 bg-[#0B0D12] border-r border-[#1F2937]/80 flex flex-col justify-between h-screen sticky top-0 px-4 py-5 select-none z-30">
      <div className="space-y-6">
        {/* Header Logo */}
        <div className="px-2 pb-2">
          <Link href="/" className="inline-block transition-transform hover:scale-[1.02]">
            <Logo size="md" showTagline={false} />
          </Link>
        </div>

        {/* Main Nav */}
        <nav className="space-y-1">
          <div className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider px-3 mb-2">
            Workspace
          </div>
          {mainNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-gradient-to-r from-indigo-600/30 to-purple-600/20 text-white border border-indigo-500/40 shadow-lg shadow-indigo-500/10'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-[#161B26]'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-gray-400'}`} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* System Nav */}
      <div className="pt-4 border-t border-[#1F2937]/70 space-y-1">
        <div className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider px-3 mb-2">
          System
        </div>
        {systemNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname.startsWith('/system') && (
            (item.name === 'Logs' && pathname.includes('logs')) ||
            (item.name === 'Jobs' && pathname.includes('jobs')) ||
            (item.name === 'Health' && pathname.includes('health'))
          );
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all ${
                isActive
                  ? 'bg-indigo-600/20 text-white'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-[#161B26]'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className="w-3.5 h-3.5 text-gray-400" />
                <span>{item.name}</span>
              </div>
              {item.badge === 'healthy' && (
                <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
              )}
            </Link>
          );
        })}

        {/* User Card */}
        <div className="mt-4 pt-3 border-t border-[#1F2937]/50 flex items-center justify-between px-2">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center text-white font-semibold text-xs border border-white/20">
              JO
            </div>
            <div className="flex flex-col">
              <span className="text-xs font-semibold text-white leading-tight">Jayant Olhyan</span>
              <span className="text-[10px] text-gray-400">Admin (Self-Hosted)</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
