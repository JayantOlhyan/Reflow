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
  Puzzle,
  Globe,
  Terminal,
  FlaskConical
} from 'lucide-react';

interface NavSection {
  title: string;
  items: {
    name: string;
    href: string;
    icon: React.ComponentType<{ className?: string }>;
    badge?: string;
  }[];
}

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  const navSections: NavSection[] = [
    {
      title: 'CORE',
      items: [
        { name: 'Overview', href: '/', icon: LayoutDashboard },
        { name: 'Content Library', href: '/content', icon: FolderOpen },
      ],
    },
    {
      title: 'CREATE',
      items: [
        { name: 'Repurpose Studio', href: '/repurpose', icon: Sparkles },
        { name: 'Carousel Studio', href: '/carousel', icon: Layers },
      ],
    },
    {
      title: 'PLAN',
      items: [
        { name: 'Calendar', href: '/calendar', icon: Calendar },
        { name: 'Automations', href: '/automations', icon: GitBranch },
        { name: 'Experiments', href: '/experiments', icon: FlaskConical },
      ],
    },
    {
      title: 'PUBLISH',
      items: [
        { name: 'Approvals', href: '/approvals', icon: ShieldCheck },
        { name: 'Publishing', href: '/publishing', icon: Layers },
        { name: 'Connections', href: '/connections', icon: Share2 },
      ],
    },
    {
      title: 'ANALYZE',
      items: [
        { name: 'Analytics', href: '/analytics', icon: BarChart3 },
        { name: 'Intelligence', href: '/intelligence', icon: Lightbulb },
      ],
    },
    {
      title: 'SYSTEM',
      items: [
        { name: 'Ecosystem Hub', href: '/ecosystem', icon: Globe },
        { name: 'Plugins', href: '/plugins', icon: Puzzle },
        { name: 'Developers API', href: '/developers', icon: Terminal },
        { name: 'System Setup', href: '/setup', icon: ShieldCheck },
        { name: 'Diagnostics', href: '/system', icon: Activity, badge: 'healthy' },
        { name: 'Settings', href: '/settings', icon: Settings },
      ],
    },
  ];

  return (
    <aside className="w-64 bg-[#0B0D12] border-r border-[#1F2937]/80 flex flex-col justify-between h-screen sticky top-0 px-4 py-5 select-none z-30 overflow-y-auto">
      <div className="space-y-5">
        {/* Header Logo */}
        <div className="px-2 pb-1">
          <Link href="/" className="inline-block transition-transform hover:scale-[1.02]">
            <Logo size="md" showTagline={false} />
          </Link>
        </div>

        {/* Grouped Workflow Nav */}
        <nav className="space-y-4">
          {navSections.map((section) => (
            <div key={section.title} className="space-y-1">
              <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest px-3 mb-1">
                {section.title}
              </div>
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive =
                  pathname === item.href ||
                  (item.href !== '/' && pathname.startsWith(item.href));
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all duration-150 ${
                      isActive
                        ? 'bg-gradient-to-r from-indigo-600/30 to-purple-600/20 text-white border border-indigo-500/40 shadow-sm shadow-indigo-500/10 font-semibold'
                        : 'text-gray-400 hover:text-gray-200 hover:bg-[#161B26]'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-gray-400'}`} />
                      <span>{item.name}</span>
                    </div>
                    {item.badge === 'healthy' && (
                      <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" />
                    )}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
      </div>

      {/* User Card */}
      <div className="pt-3 mt-4 border-t border-[#1F2937]/70 flex items-center justify-between px-2">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center text-white font-semibold text-[11px] border border-white/20">
            JO
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-semibold text-white leading-tight">Jayant Olhyan</span>
            <span className="text-[10px] text-gray-400">Admin (Self-Hosted)</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
