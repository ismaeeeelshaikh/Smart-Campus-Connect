import React, { useCallback, useEffect, useState } from 'react';
import { ExternalLink, Globe, RefreshCw, X } from 'lucide-react';
import { adminAPI } from '../../services/api';
import { apiErrorMessage } from '../../services/validation';

const formatTime = (value) => (value ? new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : '—');

const RESULT_TEXT = {
  added: 'Added to the chatbot.',
  updated: 'Changes found and updated.',
  unchanged: 'No changes since the last sync.',
  removed: 'Page no longer exists, so it was removed.',
  'no content': 'Page has no text any more, so it was removed.',
};

// Admin-only: re-read apsit.edu.in now, and see what changed
const WebsiteSyncPanel = () => {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState('');
  const [pageUrl, setPageUrl] = useState('');
  const [pageBusy, setPageBusy] = useState(false);
  const [pageResult, setPageResult] = useState('');

  const load = useCallback(async () => {
    try {
      const response = await adminAPI.websiteSyncStatus();
      setStatus(response.data);
      setError('');
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not load the sync status.'));
    }
  }, []);

  const toggleOpen = () => {
    if (!open) load(); // fetch fresh status each time the panel opens
    setOpen(!open);
  };

  // While a sync is running, refresh the progress every 3 seconds
  useEffect(() => {
    if (!open || !status?.running) return undefined;
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [open, status?.running, load]);

  const startSync = async () => {
    setError('');
    try {
      await adminAPI.startWebsiteSync();
      setStatus((s) => ({ ...(s || {}), running: true }));
      setTimeout(load, 1000);
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not start the sync.'));
    }
  };

  const syncOnePage = async (e) => {
    e.preventDefault();
    if (!pageUrl.trim()) return;
    setPageBusy(true);
    setPageResult('');
    setError('');
    try {
      const response = await adminAPI.syncOnePage(pageUrl.trim());
      const { status: result, title } = response.data;
      setPageResult(`${title ? `"${title}": ` : ''}${RESULT_TEXT[result] || result}`);
      load();
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not update that page.'));
    } finally {
      setPageBusy(false);
    }
  };

  const running = status?.running;
  const current = status?.current;
  const last = status?.last;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={toggleOpen}
        className="btn-outline px-3 py-2"
        title="Sync the chatbot with apsit.edu.in"
      >
        <RefreshCw className={`h-4 w-4 ${running ? 'animate-spin' : ''}`} />
        <span className="hidden sm:inline">Website sync</span>
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-[24rem] max-w-[calc(100vw-2rem)] animate-fade-up rounded-2xl border border-line bg-white p-5 text-sm text-ink-700 shadow-lift">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-50 text-teal-700">
                <Globe className="h-[18px] w-[18px]" />
              </span>
              <div>
                <h3 className="font-serif text-base font-semibold text-ink">Website sync</h3>
                <p className="text-xs text-ink-400">Keeps answers in step with apsit.edu.in</p>
              </div>
            </div>
            <button type="button" onClick={() => setOpen(false)} className="rounded-lg p-1 text-ink-400 hover:bg-paper-100 hover:text-ink" aria-label="Close">
              <X className="h-4 w-4" />
            </button>
          </div>

          {running ? (
            <div className="mb-4 rounded-xl border border-teal-200 bg-teal-50 p-3">
              <div className="flex items-center gap-2 font-semibold text-teal-800">
                <RefreshCw className="h-4 w-4 animate-spin" /> Syncing the whole website…
              </div>
              {current && (
                <div className="mt-1 text-xs text-teal-700">
                  {current.pages_seen} pages checked · {current.pages_added + current.pages_updated} new or changed so far
                </div>
              )}
            </div>
          ) : (
            <button type="button" onClick={startSync} className="btn-primary mb-4 w-full">
              <RefreshCw className="h-4 w-4" /> Sync whole website now
            </button>
          )}

          <form onSubmit={syncOnePage} className="mb-4 rounded-xl bg-paper-50 p-3 ring-1 ring-line">
            <label htmlFor="sync-page-url" className="mb-1.5 block text-xs font-semibold text-ink-600">
              Just edited a page? Update only that page (takes seconds)
            </label>
            <div className="flex gap-2">
              <input
                id="sync-page-url"
                type="url"
                value={pageUrl}
                onChange={(e) => setPageUrl(e.target.value)}
                placeholder="https://www.apsit.edu.in/civil-faculty"
                className="field-input min-w-0 flex-1 px-3 py-2 text-xs"
              />
              <button type="submit" disabled={pageBusy || !pageUrl.trim()} className="btn-primary px-3 py-2 text-xs">
                {pageBusy ? 'Updating…' : 'Update'}
              </button>
            </div>
            {pageResult && <div className="mt-2 text-xs font-medium text-teal-700">{pageResult}</div>}
          </form>

          {last ? (
            <div className="mb-3 space-y-1 text-xs">
              <div>
                <span className="text-ink-400">Last sync:</span> {formatTime(last.finished_at)}{' '}
                <span className={`rounded-full px-1.5 py-0.5 font-semibold ${last.status === 'success' ? 'bg-teal-50 text-teal-700' : 'bg-crimson-50 text-crimson-600'}`}>
                  {last.status}
                </span>
              </div>
              <div className="text-ink-500">
                {last.pages_seen} checked · {last.pages_added} new · {last.pages_updated} changed · {last.pages_removed} removed
                {last.pages_failed > 0 && ` · ${last.pages_failed} failed`}
              </div>
              {last.error && <div className="text-gold-700">{last.error}</div>}
            </div>
          ) : (
            !running && <div className="mb-3 text-xs text-ink-400">No sync has finished yet.</div>
          )}

          {status && <div className="mb-2 text-xs text-ink-400">Pages in the chatbot&apos;s knowledge: <strong className="text-ink-600">{status.pages_indexed}</strong></div>}

          {status?.recently_changed?.length > 0 && (
            <div>
              <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-ink-400">Recently changed pages</div>
              <ul className="scroll-thin max-h-44 space-y-1 overflow-y-auto">
                {status.recently_changed.map((p) => (
                  <li key={p.url} className="flex items-start justify-between gap-2 text-xs">
                    <a href={p.url} target="_blank" rel="noopener noreferrer" className="flex min-w-0 items-center gap-1 font-medium text-teal-700 hover:underline">
                      {p.status === 'removed' && <span className="text-crimson-600">[removed]</span>}
                      <span className="truncate">{p.title}</span>
                      <ExternalLink className="h-3 w-3 shrink-0" />
                    </a>
                    <span className="shrink-0 text-ink-400">{formatTime(p.last_changed)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {error && <div className="mt-3 text-xs font-medium text-crimson-600">{error}</div>}
        </div>
      )}
    </div>
  );
};

export default WebsiteSyncPanel;
