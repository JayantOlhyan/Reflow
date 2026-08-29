import React from 'react';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg';
  showTagline?: boolean;
  className?: string;
}

export const Logo: React.FC<LogoProps> = ({ size = 'md', showTagline = false, className = '' }) => {
  const iconSizes = {
    sm: 'w-7 h-7',
    md: 'w-9 h-9',
    lg: 'w-12 h-12'
  };

  const textSizes = {
    sm: 'text-lg',
    md: 'text-xl',
    lg: 'text-2xl'
  };

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <div className={`relative ${iconSizes[size]} flex-shrink-0 flex items-center justify-center`}>
        {/* Glow backdrop */}
        <div className="absolute inset-0 bg-gradient-to-tr from-indigo-600 via-purple-500 to-cyan-400 rounded-xl blur-[6px] opacity-60" />
        
        {/* Reflow Dynamic 'R' Mark SVG */}
        <svg viewBox="0 0 100 100" className="relative w-full h-full drop-shadow-md" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="reflowGrad" x1="10%" y1="10%" x2="90%" y2="90%">
              <stop offset="0%" stopColor="#38BDF8" />
              <stop offset="40%" stopColor="#6366F1" />
              <stop offset="85%" stopColor="#8B5CF6" />
              <stop offset="100%" stopColor="#A855F7" />
            </linearGradient>
            <filter id="shadow" x="-10%" y="-10%" width="130%" height="130%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#000000" floodOpacity="0.5"/>
            </filter>
          </defs>
          {/* Motion dots / flow trail */}
          <circle cx="18" cy="28" r="4" fill="#38BDF8" />
          <circle cx="28" cy="28" r="4" fill="#38BDF8" />
          <circle cx="14" cy="38" r="3.5" fill="#38BDF8" opacity="0.8" />
          <circle cx="24" cy="38" r="3.5" fill="#38BDF8" opacity="0.9" />
          
          {/* Continuous Ribbon R Arrow */}
          <path
            d="M38 28 H70 C82 28 88 36 88 46 C88 56 80 64 68 64 H44 C34 64 28 70 28 80 C28 85 30 89 36 89 H58 M54 54 L40 64 L54 74 Z"
            stroke="url(#reflowGrad)"
            strokeWidth="11"
            strokeLinecap="round"
            strokeLinejoin="round"
            filter="url(#shadow)"
          />
          {/* Arrow Head */}
          <path
            d="M44 64 L56 53 V75 Z"
            fill="url(#reflowGrad)"
          />
        </svg>
      </div>

      <div className="flex flex-col">
        <span className={`font-bold tracking-tight text-white ${textSizes[size]} leading-none`}>
          Reflow
        </span>
        {showTagline && (
          <span className="text-[10px] text-cyan-400 font-medium tracking-wide mt-1">
            Create once. Transform everywhere.
          </span>
        )}
      </div>
    </div>
  );
};
