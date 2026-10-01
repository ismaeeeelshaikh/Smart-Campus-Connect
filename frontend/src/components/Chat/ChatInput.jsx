import React, { useEffect, useRef, useState } from 'react';
import { ArrowUp, FileText, Mic, Paperclip, Square, X } from 'lucide-react';
import { useSpeechInput } from '../../hooks/useSpeechInput';

const MAX_LENGTH = 4000; // same limit as the backend

// The chat's PDF above the composer, or a spinner while one is being read
const PdfPill = ({ pdf, uploading, onRemove }) => (
  <div className="mb-2 flex">
    <div className="inline-flex max-w-full items-center gap-2 rounded-xl border border-teal-100 bg-teal-50 py-1.5 pl-2.5 pr-1.5 text-xs text-teal-900">
      {uploading ? (
        <>
          <span className="inline-block h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-teal-600 border-r-transparent" />
          <span className="truncate">Reading <span className="font-semibold">{uploading}</span>…</span>
        </>
      ) : (
        <>
          <FileText className="h-4 w-4 shrink-0 text-teal-700" />
          <span className="truncate font-semibold">{pdf.filename}</span>
          <span className="shrink-0 text-teal-700/70">· {pdf.pages} {pdf.pages === 1 ? 'page' : 'pages'}</span>
          {onRemove && (
            <button type="button" onClick={onRemove} className="rounded-md p-0.5 text-teal-700 hover:bg-teal-100" title="Remove PDF" aria-label="Remove PDF">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </>
      )}
    </div>
  </div>
);

/**
 * `onAttach` (optional) shows a paperclip to upload a PDF; `pdf` / `uploading` show the chat's PDF.
 */
const ChatInput = ({ onSendMessage, disabled, onAttach, pdf, uploading, onRemovePdf }) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef(null);
  const fileRef = useRef(null);
  const speech = useSpeechInput({
    onText: (text) => setMessage((prev) => (prev ? `${prev.trimEnd()} ${text}` : text).slice(0, MAX_LENGTH)),
  });

  // Grow with the text, up to ~6 lines. When empty, stay one line tall
  // (a long placeholder would otherwise make the box grow on small screens).
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    if (message) el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [message]);

  const isSmallScreen = typeof window !== 'undefined' && window.innerWidth < 640;
  const placeholder = speech.listening
    ? 'Listening… speak in English, Hindi or Hinglish'
    : pdf
      ? (isSmallScreen ? 'Ask about this PDF…' : 'Ask about this PDF or about APSIT…')
      : isSmallScreen
        ? 'Ask about APSIT…'
        : 'Ask about admissions, departments, faculty, placements…';

  const pickFile = (e) => {
    const file = e.target.files?.[0];
    e.target.value = ''; // so choosing the same file again still triggers onChange
    if (file) onAttach(file);
  };

  const send = () => {
    const text = message.trim();
    if (!text || disabled) return;
    if (speech.listening) speech.stop();
    onSendMessage(text);
    setMessage('');
  };

  const handleKeyDown = (e) => {
    // Enter sends, Shift+Enter adds a new line
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="px-4 pb-4 pt-2 sm:px-6">
      <div className="mx-auto max-w-3xl">
        {speech.error && (
          <div className="mb-2 flex items-center justify-between gap-3 rounded-xl border border-gold-200 bg-gold-50 px-3 py-2 text-xs text-gold-800">
            <span>{speech.error}</span>
            <button type="button" onClick={speech.clearError} className="font-semibold hover:underline">Dismiss</button>
          </div>
        )}
        {(pdf || uploading) && <PdfPill pdf={pdf} uploading={uploading} onRemove={disabled ? null : onRemovePdf} />}
        <form
          onSubmit={(e) => { e.preventDefault(); send(); }}
          className={`flex items-end gap-2 rounded-2xl border bg-white p-2 shadow-composer transition focus-within:border-teal-600 focus-within:ring-4 focus-within:ring-teal-700/10 ${
            speech.listening ? 'border-crimson-200' : 'border-line'
          }`}
        >
          {onAttach && (
            <>
              <input ref={fileRef} type="file" accept="application/pdf,.pdf" onChange={pickFile} className="hidden" />
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                disabled={disabled}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-ink-400 transition hover:bg-paper-100 hover:text-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
                title={pdf ? 'Replace the PDF' : 'Attach a PDF and ask about it'}
                aria-label={pdf ? 'Replace the PDF' : 'Attach a PDF'}
              >
                <Paperclip className="h-5 w-5" />
              </button>
            </>
          )}
          <textarea
            ref={textareaRef}
            rows={1}
            value={message}
            maxLength={MAX_LENGTH}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="max-h-[180px] min-h-[44px] flex-1 resize-none bg-transparent px-3 py-2.5 text-[15px] leading-relaxed text-ink placeholder-ink-300 focus:outline-none"
            aria-label="Your question"
          />
          {speech.supported && (
            <button
              type="button"
              onClick={speech.toggle}
              className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition ${
                speech.listening ? 'bg-crimson-50 text-crimson-600 hover:bg-crimson-100' : 'text-ink-400 hover:bg-paper-100 hover:text-teal-700'
              }`}
              title={speech.listening ? 'Stop voice input' : 'Speak your question'}
              aria-label={speech.listening ? 'Stop voice input' : 'Start voice input'}
            >
              {speech.listening ? <Square className="h-4 w-4 fill-current" /> : <Mic className="h-5 w-5" />}
            </button>
          )}
          <button
            type="submit"
            disabled={disabled || !message.trim()}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-700 text-white shadow-sm transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:bg-paper-300 disabled:text-white"
            title="Send"
            aria-label="Send"
          >
            <ArrowUp className="h-5 w-5" />
          </button>
        </form>
        <p className="mt-2 text-center text-[11px] text-ink-400">
          {speech.listening ? (
            <span className="inline-flex items-center gap-1.5 text-crimson-600">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-crimson-500" /> Listening — press the square to stop
            </span>
          ) : pdf ? (
            'Answers use your PDF and apsit.edu.in. Only you can see your PDF. Check important details with the college office.'
          ) : (
            'Answers are based on apsit.edu.in and may not cover everything. Check important details with the college office.'
          )}
        </p>
      </div>
    </div>
  );
};

export default ChatInput;
