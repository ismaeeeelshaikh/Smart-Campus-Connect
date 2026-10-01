import React from 'react';

// The APSIT crest in a soft badge. `size` is the badge size in px.
export const Crest = ({ size = 40, className = '' }) => (
  <span
    className={`inline-flex shrink-0 items-center justify-center rounded-full bg-white ring-1 ring-line ${className}`}
    style={{ width: size, height: size }}
  >
    <img src="/logo.png" alt="APSIT crest" className="object-contain" style={{ width: size * 0.78, height: size * 0.78 }} />
  </span>
);

// Crest + product name. `tone="light"` for use on the dark teal panel.
export const Wordmark = ({ tone = 'dark', subtitle = 'A. P. Shah Institute of Technology', size = 40 }) => (
  <div className="flex items-center gap-3">
    <Crest size={size} className={tone === 'light' ? 'ring-white/20' : ''} />
    <div className="leading-tight">
      <div className={`font-serif text-[17px] font-semibold ${tone === 'light' ? 'text-white' : 'text-teal-900'}`}>
        Smart Campus Connect
      </div>
      {subtitle && (
        <div className={`text-[11px] font-semibold uppercase tracking-[0.14em] ${tone === 'light' ? 'text-gold-300' : 'text-gold-700'}`}>
          {subtitle}
        </div>
      )}
    </div>
  </div>
);
