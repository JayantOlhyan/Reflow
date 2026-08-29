"use client";

import React from 'react';
import { Eye, ThumbsUp, MessageSquare, Share2, TrendingUp } from 'lucide-react';
import { YoutubeIcon, InstagramIcon, LinkedinIcon, XIcon } from '@/components/ui/SocialIcons';

export default function AnalyticsPage() {
  const stats = [
    { label: 'Total Impressions', value: '428.5K', change: '+24.8%', icon: Eye, color: 'text-indigo-400' },
    { label: 'Engagements', value: '38.2K', change: '+18.2%', icon: ThumbsUp, color: 'text-emerald-400' },
    { label: 'Comments & Replies', value: '2.4K', change: '+32.1%', icon: MessageSquare, color: 'text-purple-400' },
    { label: 'Cross-Shares', value: '940', change: '+14.5%', icon: Share2, color: 'text-cyan-400' },
  ];

  const platformPerformance = [
    { platform: 'YouTube Shorts', views: '210.4K', likes: '18.2K', ctr: '8.4%', icon: YoutubeIcon, color: 'text-red-400' },
    { platform: 'Instagram Reels', views: '145.2K', likes: '12.4K', ctr: '6.2%', icon: InstagramIcon, color: 'text-pink-400' },
    { platform: 'LinkedIn Posts', views: '48.9K', likes: '4.8K', ctr: '11.8%', icon: LinkedinIcon, color: 'text-blue-400' },
    { platform: 'X / Twitter', views: '24.0K', likes: '2.8K', ctr: '4.5%', icon: XIcon, color: 'text-gray-300' },
  ];

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Analytics & Distribution</h1>
        <p className="text-xs text-gray-400 mt-0.5">Aggregate performance metrics across connected platforms.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="bg-[#111827] border border-[#1F2937] rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-400">{stat.label}</span>
                <Icon className={`w-4 h-4 ${stat.color}`} />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-white tracking-tight">{stat.value}</span>
                <span className="text-xs font-semibold text-emerald-400 flex items-center">
                  {stat.change} <TrendingUp className="w-3 h-3 ml-0.5" />
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 space-y-4">
        <h2 className="text-base font-bold text-white">Platform Performance Breakdown</h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[#1F2937] text-gray-400 font-semibold">
                <th className="pb-3">Platform</th>
                <th className="pb-3">Views / Impressions</th>
                <th className="pb-3">Likes & Reactions</th>
                <th className="pb-3">Engagement Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1F2937]">
              {platformPerformance.map((item) => {
                const Icon = item.icon;
                return (
                  <tr key={item.platform} className="hover:bg-[#161B26] transition-colors">
                    <td className="py-3.5 flex items-center gap-2.5 font-bold text-white">
                      <Icon className={`w-4 h-4 ${item.color}`} />
                      <span>{item.platform}</span>
                    </td>
                    <td className="py-3.5 text-gray-300 font-mono">{item.views}</td>
                    <td className="py-3.5 text-gray-300 font-mono">{item.likes}</td>
                    <td className="py-3.5 text-emerald-400 font-bold font-mono">{item.ctr}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
