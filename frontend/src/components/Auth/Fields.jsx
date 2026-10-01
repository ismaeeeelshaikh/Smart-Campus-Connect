import React, { useState } from 'react';
import { AlertCircle, CheckCircle2, Eye, EyeOff } from 'lucide-react';

// Labelled input with an optional leading icon and hint text
export const TextField = ({ label, icon: Icon, hint, id, ...props }) => (
  <div>
    <label htmlFor={id} className="field-label">{label}</label>
    <div className="relative">
      {Icon && <Icon className="pointer-events-none absolute left-3.5 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-ink-400" />}
      <input id={id} className={`field-input ${Icon ? 'pl-11' : ''}`} {...props} />
    </div>
    {hint && <p className="mt-1.5 text-xs text-ink-400">{hint}</p>}
  </div>
);

// Password input with a show / hide toggle
export const PasswordField = ({ label, icon: Icon, hint, id, ...props }) => {
  const [visible, setVisible] = useState(false);
  return (
    <div>
      <label htmlFor={id} className="field-label">{label}</label>
      <div className="relative">
        {Icon && <Icon className="pointer-events-none absolute left-3.5 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-ink-400" />}
        <input id={id} type={visible ? 'text' : 'password'} className={`field-input pr-11 ${Icon ? 'pl-11' : ''}`} {...props} />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-ink-400 transition hover:bg-paper-200 hover:text-ink"
          aria-label={visible ? 'Hide password' : 'Show password'}
        >
          {visible ? <EyeOff className="h-[18px] w-[18px]" /> : <Eye className="h-[18px] w-[18px]" />}
        </button>
      </div>
      {hint && <p className="mt-1.5 text-xs text-ink-400">{hint}</p>}
    </div>
  );
};

export const ErrorAlert = ({ children }) =>
  children ? (
    <div className="alert-error animate-fade-up" role="alert">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{children}</span>
    </div>
  ) : null;

export const SuccessAlert = ({ children }) =>
  children ? (
    <div className="alert-success animate-fade-up" role="status">
      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{children}</span>
    </div>
  ) : null;

export const Spinner = ({ className = 'h-4 w-4' }) => (
  <span className={`inline-block animate-spin rounded-full border-2 border-current border-r-transparent ${className}`} aria-hidden="true" />
);
