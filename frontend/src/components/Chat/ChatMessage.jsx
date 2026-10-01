import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Check, Copy, ExternalLink, FileText } from 'lucide-react';
import { Crest } from '../Brand/Brand';

const CITATION_MARKS = /【[^】]*】/g; // the backend removes these too; hide them while streaming

const formatTime = (value) => {
  const date = value ? new Date(value) : null;
  return date && !Number.isNaN(date.getTime()) ? date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
};

const markdownComponents = {
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
  ),
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto rounded-xl border border-line">
      <table className="my-0">{children}</table>
    </div>
  ),
};

export const TypingDots = () => (
  <div className="flex items-center gap-1.5 py-2" aria-label="Assistant is typing">
    {[0, 1, 2].map((i) => (
      <span key={i} className="h-2 w-2 animate-dot-bounce rounded-full bg-gold-500" style={{ animationDelay: `${i * 0.15}s` }} />
    ))}
  </div>
);

const SourceChips = ({ sources }) => (
  <div className="mt-4 border-t border-paper-200 pt-3">
    <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-ink-400">Sources</div>
    <div className="flex flex-wrap gap-2">
      {sources.map((s) => {
        const isPdf = /\.pdf$/i.test(s.url);
        const Icon = isPdf ? FileText : ExternalLink;
        return (
          <a
            key={s.url}
            href={s.url}
            target="_blank"
            rel="noopener noreferrer"
            title={s.url}
            className="inline-flex max-w-full items-center gap-1.5 rounded-lg border border-teal-100 bg-teal-50 px-2.5 py-1 text-xs font-medium text-teal-800 transition hover:border-teal-300 hover:bg-teal-100"
          >
            <Icon className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{s.title.replace(/ \(PDF\)$/, '').replace(/_/g, ' ')}</span>
          </a>
        );
      })}
    </div>
  </div>
);

const CopyButton = ({ text }) => {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard not available */
    }
  };
  return (
    <button
      type="button"
      onClick={copy}
      className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-ink-400 transition hover:bg-paper-100 hover:text-ink"
      title="Copy answer"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-teal-600" /> : <Copy className="h-3.5 w-3.5" />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  );
};

const ChatMessage = ({ message }) => {
  if (message.type === 'user') {
    return (
      <div className="flex animate-fade-up justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-tr-md bg-teal-700 px-4 py-3 text-[15px] leading-relaxed text-white shadow-sm sm:max-w-[75%]">
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
          <div className="mt-1 text-right text-[11px] text-teal-100/70">{formatTime(message.timestamp)}</div>
        </div>
      </div>
    );
  }

  const content = (message.content || '').replace(CITATION_MARKS, '');
  const waiting = message.streaming && !content;

  return (
    <div className="flex animate-fade-up gap-3">
      <Crest size={34} className="mt-1 hidden sm:inline-flex" />
      <div className="min-w-0 flex-1 rounded-2xl rounded-tl-md border border-line bg-white px-5 py-4 shadow-card">
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="font-serif text-sm font-semibold text-teal-900">Smart Campus Connect</span>
          {!message.streaming && <span className="text-[11px] text-ink-300">{formatTime(message.timestamp)}</span>}
        </div>
        {waiting ? (
          <TypingDots />
        ) : (
          <div className="prose prose-sm max-w-none break-words text-[15px] leading-relaxed sm:prose-base sm:text-[15px]">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
              {content}
            </ReactMarkdown>
            {message.streaming && <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 animate-caret bg-teal-700" />}
          </div>
        )}
        {!message.streaming && message.sources?.length > 0 && <SourceChips sources={message.sources} />}
        {!message.streaming && content && (
          <div className="mt-2 flex justify-end">
            <CopyButton text={content} />
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
