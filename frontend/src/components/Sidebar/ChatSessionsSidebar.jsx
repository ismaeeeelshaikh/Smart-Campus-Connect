import React, { useState } from 'react';
import { Check, LogOut, MessageSquareText, Pencil, Plus, Trash2, X } from 'lucide-react';
import { Wordmark } from '../Brand/Brand';

const relativeTime = (value) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const minutes = Math.floor((Date.now() - date.getTime()) / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days} days ago`;
  return date.toLocaleDateString([], { day: 'numeric', month: 'short' });
};

const initials = (name = '') =>
  name.split(/[\s._-]+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join('') || '?';

const SessionItem = ({ session, active, onSelect, onRename, onDelete }) => {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(session.title);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const save = async () => {
    setEditing(false);
    if (title.trim() && title.trim() !== session.title) await onRename(session.id, title.trim());
    else setTitle(session.title);
  };

  if (editing) {
    return (
      <div className="flex items-center gap-1 rounded-xl bg-teal-50 px-2 py-2">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') save();
            if (e.key === 'Escape') { setTitle(session.title); setEditing(false); }
          }}
          onBlur={save}
          maxLength={100}
          autoFocus
          className="min-w-0 flex-1 rounded-lg border border-teal-300 bg-white px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-teal-700/15"
          aria-label="Chat title"
        />
      </div>
    );
  }

  return (
    <div
      className={`group relative flex cursor-pointer items-start gap-2.5 rounded-xl px-3 py-2.5 transition ${
        active ? 'bg-teal-50' : 'hover:bg-paper-100'
      }`}
      onClick={() => onSelect(session.id)}
      onKeyDown={(e) => e.key === 'Enter' && onSelect(session.id)}
      role="button"
      tabIndex={0}
      aria-current={active ? 'true' : undefined}
    >
      {active && <span className="absolute inset-y-2 left-0 w-[3px] rounded-full bg-gold-500" />}
      <MessageSquareText className={`mt-0.5 h-4 w-4 shrink-0 ${active ? 'text-teal-700' : 'text-ink-300'}`} />
      <div className="min-w-0 flex-1">
        <div className={`truncate text-sm ${active ? 'font-semibold text-teal-900' : 'text-ink-700'}`}>{session.title}</div>
        <div className="mt-0.5 text-[11px] text-ink-400">{relativeTime(session.updated_at)}</div>
      </div>

      {confirmDelete ? (
        <div className="flex shrink-0 items-center gap-0.5" onClick={(e) => e.stopPropagation()}>
          <span className="mr-1 text-[11px] font-semibold text-crimson-600">Delete?</span>
          <button type="button" onClick={() => onDelete(session.id)} className="rounded-md p-1 text-crimson-600 hover:bg-crimson-50" aria-label="Confirm delete">
            <Check className="h-3.5 w-3.5" />
          </button>
          <button type="button" onClick={() => setConfirmDelete(false)} className="rounded-md p-1 text-ink-400 hover:bg-paper-200" aria-label="Cancel">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : (
        <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition group-hover:opacity-100 group-focus-within:opacity-100" onClick={(e) => e.stopPropagation()}>
          <button type="button" onClick={() => setEditing(true)} className="rounded-md p-1 text-ink-400 hover:bg-paper-200 hover:text-teal-700" title="Rename">
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button type="button" onClick={() => setConfirmDelete(true)} className="rounded-md p-1 text-ink-400 hover:bg-crimson-50 hover:text-crimson-600" title="Delete">
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  );
};

const ChatSessionsSidebar = ({
  sessions, sessionsLoaded, currentSession, onNewChat, onSelectSession, onUpdateTitle, onDeleteSession, user, onLogout,
}) => (
  <div className="flex h-full w-[280px] flex-col border-r border-line bg-white">
    <div className="px-5 pb-4 pt-5">
      <Wordmark size={38} subtitle="APSIT Thane" />
    </div>
    <div className="px-4">
      <button type="button" onClick={onNewChat} className="btn-primary w-full py-3">
        <Plus className="h-[18px] w-[18px] text-gold-300" /> New chat
      </button>
    </div>

    <div className="mt-6 px-5 text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-400">Recent chats</div>
    <div className="scroll-thin mt-2 min-h-0 flex-1 space-y-0.5 overflow-y-auto px-3 pb-3">
      {!sessionsLoaded ? (
        [0, 1, 2].map((i) => <div key={i} className="mx-1 h-12 animate-pulse rounded-xl bg-paper-100" />)
      ) : sessions.length === 0 ? (
        <div className="mx-2 mt-2 rounded-xl border border-dashed border-line px-4 py-6 text-center text-sm text-ink-400">
          No chats yet. Ask your first question!
        </div>
      ) : (
        sessions.map((session) => (
          <SessionItem
            key={session.id}
            session={session}
            active={currentSession?.id === session.id}
            onSelect={onSelectSession}
            onRename={onUpdateTitle}
            onDelete={onDeleteSession}
          />
        ))
      )}
    </div>

    {user && (
      <div className="flex items-center gap-3 border-t border-line px-4 py-4">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-teal-800 text-sm font-semibold text-gold-300">
          {initials(user.username)}
        </span>
        <div className="min-w-0 flex-1 leading-tight">
          <div className="truncate text-sm font-semibold text-ink">{user.username}</div>
          <div className="truncate text-xs text-ink-400">{user.email}</div>
        </div>
        <button type="button" onClick={onLogout} className="rounded-lg p-2 text-ink-400 transition hover:bg-paper-100 hover:text-crimson-600" title="Sign out" aria-label="Sign out">
          <LogOut className="h-[18px] w-[18px]" />
        </button>
      </div>
    )}
  </div>
);

export default ChatSessionsSidebar;
