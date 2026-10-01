import React, { useEffect, useRef } from 'react';
import { AlertCircle, Briefcase, Building2, CalendarCheck, GraduationCap, RotateCcw, X } from 'lucide-react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import { Crest } from '../Brand/Brand';

const SUGGESTIONS = [
  { icon: GraduationCap, label: 'Departments & faculty', question: 'Who is the HOD of Computer Engineering?' },
  { icon: CalendarCheck, label: 'Admissions', question: 'What are the upcoming admission dates?' },
  { icon: Briefcase, label: 'Placements', question: 'Which companies recruit from APSIT?' },
  { icon: Building2, label: 'Campus & facilities', question: 'What facilities are available on campus?' },
];

const Welcome = ({ onPick, greeting }) => (
  <div className="mx-auto flex min-h-full max-w-3xl flex-col items-center justify-center px-2 py-10 text-center">
    <Crest size={64} className="shadow-card" />
    <div className="mt-5 h-0.5 w-12 rounded bg-gold-500" />
    <h1 className="mt-5 font-serif text-3xl font-semibold tracking-tight text-ink sm:text-4xl">{greeting}</h1>
    <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-ink-500">
      Ask about admissions, departments, faculty, facilities or placements at A. P. Shah Institute of Technology.
      Answers come from the college website, with links to the source.
    </p>
    <p className="mt-2 text-sm text-teal-700">Ask in English, हिंदी, मराठी or Hinglish — you&apos;ll get the answer in the same language.</p>
    <div className="mt-8 grid w-full gap-3 sm:grid-cols-2">
      {SUGGESTIONS.map(({ icon: Icon, label, question }) => (
        <button
          key={label}
          type="button"
          onClick={() => onPick(question)}
          className="group flex items-start gap-3 rounded-2xl border border-line bg-white p-4 text-left shadow-card transition hover:-translate-y-0.5 hover:border-teal-300 hover:shadow-lift"
        >
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-700 transition group-hover:bg-teal-700 group-hover:text-white">
            <Icon className="h-5 w-5" />
          </span>
          <span>
            <span className="block text-sm font-semibold text-ink">{label}</span>
            <span className="mt-0.5 block text-sm text-ink-500">{question}</span>
          </span>
        </button>
      ))}
    </div>
  </div>
);

const ErrorBanner = ({ error, failedQuestion, onRetry, onDismiss }) => (
  <div className="alert-error animate-fade-up items-center justify-between" role="alert">
    <span className="flex items-start gap-2">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      {error}
    </span>
    <span className="flex shrink-0 items-center gap-1">
      {failedQuestion && onRetry && (
        <button type="button" onClick={() => onRetry(failedQuestion)} className="inline-flex items-center gap-1 rounded-lg px-2 py-1 font-semibold hover:bg-crimson-100">
          <RotateCcw className="h-3.5 w-3.5" /> Try again
        </button>
      )}
      {onDismiss && (
        <button type="button" onClick={onDismiss} className="rounded-lg p-1 hover:bg-crimson-100" aria-label="Dismiss">
          <X className="h-4 w-4" />
        </button>
      )}
    </span>
  </div>
);

/**
 * The conversation + composer. Used by both the student chat and the guest chat.
 */
const ChatInterface = ({
  messages,
  onSendMessage,
  loading,
  loadingSession = false,
  error,
  failedQuestion,
  onDismissError,
  greeting = 'Ask anything about APSIT',
}) => {
  const scrollRef = useRef(null);
  const lastContent = messages.length ? messages[messages.length - 1].content : '';

  // Keep the newest text in view while an answer streams in (not on the welcome screen)
  useEffect(() => {
    const el = scrollRef.current;
    if (el && messages.length) el.scrollTo({ top: el.scrollHeight, behavior: loading ? 'auto' : 'smooth' });
  }, [messages.length, lastContent, loading]);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div ref={scrollRef} className="scroll-thin min-h-0 flex-1 overflow-y-auto bg-paper bg-paper-grid bg-grid">
        {loadingSession ? (
          <div className="flex h-full items-center justify-center text-sm text-ink-400">
            <span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-teal-600 border-r-transparent" />
            Opening chat…
          </div>
        ) : messages.length === 0 ? (
          <div className="h-full px-4">
            <Welcome onPick={onSendMessage} greeting={greeting} />
            {error && (
              <div className="mx-auto max-w-3xl pb-6">
                <ErrorBanner error={error} failedQuestion={failedQuestion} onRetry={onSendMessage} onDismiss={onDismissError} />
              </div>
            )}
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-6 px-4 py-8 sm:px-6">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            {error && <ErrorBanner error={error} failedQuestion={failedQuestion} onRetry={onSendMessage} onDismiss={onDismissError} />}
          </div>
        )}
      </div>
      <div className="border-t border-line/70 bg-paper">
        <ChatInput onSendMessage={onSendMessage} disabled={loading || loadingSession} />
      </div>
    </div>
  );
};

export default ChatInterface;
