import React from 'react';
import { BookOpenCheck, RefreshCw, ShieldCheck } from 'lucide-react';
import { Crest, Wordmark } from '../Brand/Brand';

const FEATURES = [
  { icon: ShieldCheck, title: 'Answers from apsit.edu.in', text: 'Built on the college website: departments, faculty, admissions, notices.' },
  { icon: RefreshCw, title: 'Kept up to date', text: 'When the website changes, the assistant learns it automatically.' },
  { icon: BookOpenCheck, title: 'Sources with every answer', text: 'Each answer links the official page it came from.' },
];

/**
 * Split screen used by all sign-in / sign-up pages: brand panel on the left (on top on mobile),
 * the form card on the right.
 */
const AuthLayout = ({ eyebrow, title, subtitle, children, footer }) => (
  <div className="min-h-screen bg-paper lg:grid lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
    {/* Brand panel */}
    <aside className="relative hidden overflow-hidden bg-gradient-to-br from-teal-950 via-teal-900 to-teal-700 px-12 py-12 text-white lg:flex lg:flex-col">
      <div className="pointer-events-none absolute inset-0 bg-crest-grid bg-grid" />
      <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-gold-500/10 blur-3xl" />

      <div className="relative flex items-center gap-3">
        <Crest size={52} className="ring-white/25" />
        <div className="leading-tight">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-gold-300">Thane · Maharashtra</div>
          <div className="text-sm text-teal-50/90">A. P. Shah Institute of Technology</div>
        </div>
      </div>

      <div className="relative mt-16 max-w-lg">
        <div className="mb-6 h-0.5 w-20 rounded bg-gold-500" />
        <h1 className="font-serif text-5xl font-semibold leading-[1.05] tracking-tight">
          Smart Campus
          <span className="block italic text-teal-200">Connect</span>
        </h1>
        <p className="mt-5 text-lg leading-relaxed text-teal-50/85">
          Ask anything about APSIT: admissions, departments, faculty, facilities and placements.
        </p>
      </div>

      <ul className="relative mt-12 max-w-lg space-y-3">
        {FEATURES.map(({ icon: Icon, title: t, text }) => (
          <li key={t} className="flex gap-4 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/10 text-gold-300">
              <Icon className="h-5 w-5" />
            </span>
            <div>
              <div className="font-semibold">{t}</div>
              <div className="mt-0.5 text-sm leading-relaxed text-teal-50/70">{text}</div>
            </div>
          </li>
        ))}
      </ul>

      <div className="relative mt-auto border-t border-white/10 pt-6 text-sm text-teal-50/60">
        AI assistant for students, parents and applicants of A. P. Shah Institute of Technology, Thane.
      </div>
    </aside>

    {/* Form side */}
    <main className="flex min-h-screen flex-col px-5 py-8 sm:px-10 lg:px-16">
      <div className="lg:hidden">
        <Wordmark />
      </div>
      <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-10">
        {eyebrow && (
          <span className="mb-4 inline-flex w-fit items-center rounded-full bg-gold-100 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-gold-800">
            {eyebrow}
          </span>
        )}
        <h2 className="font-serif text-3xl font-semibold tracking-tight text-ink sm:text-4xl">{title}</h2>
        {subtitle && <p className="mt-2 text-[15px] leading-relaxed text-ink-500">{subtitle}</p>}
        <div className="mt-8">{children}</div>
        {footer && <div className="mt-8">{footer}</div>}
      </div>
    </main>
  </div>
);

export default AuthLayout;
